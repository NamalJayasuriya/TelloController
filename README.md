# TelloController

This project is a modified version of cocopy/Tello-Python Project
https://github.com/cocpy/Tello-Python

    Control DJI Tello drone with python


## Installation
    pip install tello-python


## How to import
    import tello
    
    drone = tello.Tello()


## Examples
    import tello
    
    drone = tello.Tello()
    
    drone.takeoff()
    
    drone.forward(100)
    
    drone.cw(90)
    
    drone.flip('r')
    
    drone.streamon()
    
    drone.land()
    

### Distance
    Required. The distance to fly forward in cm. Has to be between 20 and 500.


### Degrees
    Required. The number of degrees to rotate. Has to be between 1 and 360.


## More
    For more commands, please refer to the methods and comments in the source code tello.py file