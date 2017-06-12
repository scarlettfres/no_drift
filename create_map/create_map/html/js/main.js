
console.log("defining module");
angular.module('pepper-ManualExploration', ['ngTouch'])
    .controller('map-display', function ($scope, $locale, $timeout, $http) {
        console.log("map-display controller");
        var memory = null;
        var exploManager = null;
        var intervalID = null;
        var mpp = null;
        var size = null;
        var offset = null;
        // step : 0 = list explo, 1 = reloc, 2 = ManualExploration.
        var step = 0;
        var touch = null;

        $scope.setMap = function (tab) {
            var mpp = tab[0];
            var size = tab[1];
            var offset = tab[2];
            var data = tab[3];
            var wrapper = document.getElementById("wrapper");
            wrapper.style = "position:relative; width:"+size+"px; height:"+size+"px;"
            var map_container = document.getElementById('map_container');
            map_container.width = size;
            map_container.height = size;
            angular.element(map_container).css({
            'background-image': 'url(' + data +')',
            'background-size' : 'cover'
            });
            var waypoint_canvas = document.getElementById("waypoints_canvas");
            waypoint_canvas.width = size;
            waypoint_canvas.height = size;
            var places_canvas = document.getElementById("places_canvas");
            places_canvas.width = size;
            places_canvas.height = size;
            step = 1;
            document.getElementById("waiting_ui").style.display = "none";
            document.getElementById("mode_ui").style.visibility = "visible";
            document.getElementById("waypoints_ui").style.visibility = "visible";
        };

        $scope.setRobot = function (tab) {
            console.log("setRobot");
            var centerX = tab[0][0];
            var centerY = tab[0][1];
            var radius = tab[1];
            var canvas = document.getElementById('map_container');
            var context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.beginPath();
            context.arc(centerX, centerY, radius, 0, 2 * Math.PI, false);
            context.fillStyle="blue";
            context.fill();
            context.beginPath();
            context.arc(tab[2][0], tab[2][1], 0.5 * radius, 0, 2 * Math.PI, false);
            context.fillStyle="blue";
            context.fill();
        };

        $scope.OnExit = function() {
            memory.raiseEvent("ManualExploration/Exit", [])
        }

        $scope.OnStop = function() {
            memory.raiseEvent("ManualExploration/StopManualExploration", [])
        }
        
        $scope.OnStart = function() {
            memory.raiseEvent("ManualExploration/StopManualExploration", [])
        }

    
        var onConnected = function (session) {
            session.service("ALMemory").then(function (service) {
                memory = service;
            }, function (error) {
            });
            session.service("ExplorationManager").then(function (service) {
                exploManager = service;
                exploManager.publishMap()
                exploManager.publishLabels()
            }, function (error) {
            });
            RobotUtils.subscribeToALMemoryEvent("ExplorationManager/MetricalMap", $scope.setMap);
            RobotUtils.subscribeToALMemoryEvent("ManualExploration/RobotPosition", $scope.setRobot);
            RobotUtils.subscribeToALMemoryEvent("ExplorationManager/Places", $scope.setPlaces);
            RobotUtils.subscribeToALMemoryEvent("ManualExploration/Waypoints", $scope.setWaypoints);
            RobotUtils.subscribeToALMemoryEvent("ManualExploration/ManualExplorationStarted", $scope.onManualExplorationStarted);
            RobotUtils.subscribeToALMemoryEvent("ManualExploration/ManualExplorationFinished", $scope.onManualExplorationFinished);

        };

        var onDisconnected = function () {
        };

        RobotUtils.connect(onConnected, onDisconnected);

    });

var click = function (x, y) {
    var ev = document.createEvent('TouchEvent');
    var el = document.elementFromPoint(x, y);
    ev.initUIEvent('touchstart', true, true );
    el.dispatchEvent(ev);
}
