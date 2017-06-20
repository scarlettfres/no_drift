import qi
import os
import time
import threading
import cv2
import numpy as np
import almath as m
import base64
import sys
import functools
import math
import almath
try:
    import cPickle as pickle
except:
    import pickle

try:
    from almath import OccupancyMapParams
    from almath import Point2Di
except:
    class Point2Di:

        def __init__(self, x, y):
            self.x = x
            self.y = y

    class OccupancyMapParams:

        def __init__(self, size, metersPerPixel, originOffest):
            self.size = size
            self.metersPerPixel = metersPerPixel
            # Metric coordinates of the (0, 0) pixel.
            self.originOffset = m.Position2D(0, 0)
            self.originOffset.x = originOffest.x
            self.originOffset.y = originOffest.y

        def getPositionFromPixel(self, pixel):
            return m.Position2D(pixel.x * self.metersPerPixel + self.originOffset.x, -pixel.y * self.metersPerPixel + self.originOffset.y)

        def getPixelFromPosition(self, position):
            return m.Position2D((position.x - self.originOffset.x) / self.metersPerPixel, (self.originOffset.y - position.y) / self.metersPerPixel)


@qi.multiThreaded()
class EventHelper:

    def __init__(self, memory, subscribers):
        self.subscribers = subscribers
        self.memory = memory
        self.serviceName = "EventHelper"
        self.subscribeToggle = False
        self.connectSubscribers()

    @qi.bind()
    def connectSubscribers(self):
        """ generate & connect all subscribers to callbacks """
        if not self.subscribeToggle:
            for event in self.subscribers.keys():
                self.subscribers[event][
                    "subscriber"] = self.memory.subscriber(event)
                self.subscribers[event]["uid"] = self.subscribers[event][
                    "subscriber"].signal.connect(self.subscribers[event]["callback"])
            self.subscribeToggle = True

    @qi.bind()
    def disconnectSubscribers(self):
        """ disconnect all subscribers from callbacks """
        qi.info(self.serviceName, "DISCONNECTING SUBSCRIBERS")
        if self.subscribeToggle:
            for event in self.subscribers.keys():
                future = qi.async(self.disconnectSubscriber, event, delay=0)
                future.wait(1000)  # add a timeout to avoid deadlock
                if not future.isFinished():
                    qi.error(self.serviceName, "disconnectSubscribers",
                             "Failed disconnecting %s subscribers" % event)
            self.subscribeToggle = False


class NoDriftManager:

    def __new__(cls, session):
        return super(NoDriftManager, cls).__new__(cls)

    def __init__(self, session):
        self.session = session
        self.nav = self.session.service("ALNavigation")
        self.motion = self.session.service("ALMotion")
        self.tabletService = self.session.service("ALTabletService")
        self.memory = self.session.service("ALMemory")
        self.tts = self.session.service("ALTextToSpeech")
        self.application_name = "NoDriftManager"
        self.explorer_application_name = "Explorer"
        self.current_places = None
        self.logger = qi.Logger("NoDriftManager")
        self.explo_extension = ".explo"
        self.places_extension = ".places"
        self.packageUid = "exploration-manager"
        #self.timerNoDrift = TimerNoDrift(3, self.nav, self.tts)
        self.subscribers = {
            "Places/LoadPlaces": {"callback": self.loadPlaces},
            "Places/Start": {"callback": self.startDriftCallback},
            "Places/Stop": {"callback": self.stopDriftCallback}
        }
        
        self.events = {"metricalMap": "ExplorationManager/MetricalMap",
                       "places": "ExplorationManager/Places"}
        self.eventHelper = EventHelper(self.memory, self.subscribers)
        self.noDrift = qi.PeriodicTask()
        self.noDrift.setCallback(self.replace)
        self.noDrift.setUsPeriod(3000000)
            
    def isExplorationLoaded(self):
        try:
            self.nav.getExplorationPath()
            places_loaded = "name" in self.current_places and "places" in self.current_places
        except:
            return False
        return places_loaded

    def isLocalized(self):
        try:
            self.nav.getRobotPositionInMap()
            return True
        except:
            return False

    def getPlaces(self):
        if self.current_places == None:
            self.logger.warning("No places loaded")
            return None
        return self.current_places["places"]
        
    def replace(self):
        try:
            robotPose = m.Pose2D(self.nav.getRobotPositionInMap()[0])
            center = m.Pose2D(0.0, 0.0, 0.0)
            if robotPose.distance(center) > 0.3:
        	self.tts.say("up")
                self.nav.navigateToInMap([0.0, 0.0])
            if robotPose.distance(center) < 0.3:
                poseDiff = robotPose.diff(center)
                if math.fabs(poseDiff.theta) > 0.2:
		    self.tts.say("up")
                    self.motion.moveTo(0, 0, almath.modulo2PI(poseDiff.theta))
                    self.logger.info("moveTo theta : " + str(poseDiff.theta) )
                
        except Exception as e:
            self.logger.error("RobotNotlocalized" + str(e))

        
    def startDriftCallback(self, useless):
        self.logger.warning("startDriftCallback")
        self.noDrift.start(True)
        return True
   
    def stopDriftCallback(self, useless):
        self.logger.warning("stopDriftCallback")
        self.noDrift.stop()
        self.nav.stopLocalization()
        return 0

    def loadExploration(self, name):
        self.nav.stopLocalization()
        explo_path = qi.path.findData(
            self.explorer_application_name, name + self.explo_extension, False)
        if len(explo_path) > 0:
            try:
                if not(self.nav.loadExploration(explo_path)):
                    return False
                self.current_places = {}
                self.current_places["name"] = name
                self.current_places["places"] = {}
            except Exception as e:
                self.logger.error("Unable to load explo: " + str(e))
                return False
            return True
        self.logger.error("No such explo file: " + name)
        return False

    def loadPlaces(self, name):
        self.logger.info("load places")
        available_explo = qi.path.findData(
            self.application_name, name + self.places_extension, False)
        if len(available_explo) > 0:
            # load an existing annotated explo
            in_file = open(available_explo, "rb")
            data = pickle.load(in_file)
            in_file.close()
            if not("name" in data) or not("places" in data):
                self.logger.error("wrong annoted explo format")
                return False
            self.current_places = data
            explo_path = qi.path.findData(
                self.explorer_application_name, name + self.explo_extension, False)
            if len(explo_path) > 0:
                try:
                    self.nav.loadExploration(explo_path)
                except Exception as e:
                    self.logger.warning("Unable to load places: " + str(e))
                    return False
            else:
                return False
        elif not(self.loadExploration(name)):
            return False
        self.showPlaces()
        return True

    def getAvailableExplorations(self):
        data = qi.path.listData(
            self.explorer_application_name, "*" + self.explo_extension)
        return self.getBasenameList(data)

    def getAvailablePlaces(self):
        data = qi.path.listData(self.application_name,
                                "*" + self.places_extension)
        return self.getBasenameList(data)

    def getBasenameList(self, data):
        result = []
        for path in data:
            basename = os.path.basename(path)
            result.append(basename[:len(basename) - 6])
        return result

    def showWebPage(self):
        appName = self.packageUid
        if self.tabletService.loadApplication(appName):
            self.logger.info("Successfully set application: %s" % appName)
            self.tabletService.showWebview()
            time.sleep(4)
            return True
        else:
            self.logger.warning(
                "Got tablet service, but failed to set application: %s" % appName)
            return False

    def showPlaces(self):
        self.publishMap()

    def publishMap(self):
        if self.current_places == None:
            self.logger.warning("No places loaded")
            return None
        # Get the map from navigation.
        map = self.nav.getMetricalMap()
        mpp = map[0]
        size = map[1]
        originOffset = m.Position2D(map[3])
        data = map[4]
        # Fit the size of the image
        img = np.array(data, np.uint8).reshape(size, size, 1)
        img = (100 - img) * 2.5
        img = img.transpose((1, 0, 2))  # Do not transpose the channels.
        tabletSize = 736
        img = cv2.resize(img, (tabletSize, tabletSize))
        mpp = size * mpp / tabletSize
        size = tabletSize
        # convert to color
        cv_img = img.astype(np.uint8)
        color_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
        self.occMap = OccupancyMapParams(size, mpp, originOffset)
        self.occMap.originOffset = originOffset
        # png
        flag, buff = cv2.imencode(".png", color_img)
        # base 64
        buff64 = base64.b64encode(buff)
        full = "data:image/png;base64," + buff64
        # show app
        self.memory.raiseEvent(self.events["metricalMap"], [
                               mpp, size, map[3], full])

    def getOccupancyMapParams(self):
        return [self.occMap.size, self.occMap.metersPerPixel, self.occMap.originOffset.toVector()]

if __name__ == "__main__":
    app = qi.Application(sys.argv)
    app.start()
    session = app.session

    # get the logs
    mod = qi.module("qicore")
    provider = mod.initializeLogging(app.session)

    # don't forget to check that the services you use are ready!
    for required_service in ["ALMemory", "ALNavigation", "ALTabletService"]:
        future = session.waitForService(required_service)
        if future is not None:
            future.wait()
    my_service = NoDriftManager(session)
    register_id = session.registerService("NoDriftManager", my_service)
    app.run()
