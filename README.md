# no_drift project 

## create_map

When this app is launched, the robot start to learn a map, make a 360 turn, then save the "exploration" into .explo file.
When done, it shows the map then quit after few seconds.

## no_drift app  

When this app is installed, a service with a periodic task will start with naoqi. 
The app ask us to load a map, and click on the map to relocalize. It shows the localized pose of the robot in the map, so we can restart the relocalization process if needed. Then we start/stop the periodic task that replace the robot in pose (0, 0, 0).
