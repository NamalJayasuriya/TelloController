from pynput import keyboard
import  tello

class DroneController(object):

    def __init__(self, drone):

        # control variables
        self.distance = 20  # default distance for '15move' cmd
        self.degree = 30  # defaul
        # t degree for 'cw' or 'ccw' cmd
        self.log_seqence = 0 #sequence number of last log
        self.log_update = 0 #latest sequence number
        self.controller = False
    def on_press(self, key):
        if key == 'exit':
            if drone.get_height()>0:
                print("Requesting to Land")
                drone.land()
            else:
                print(" Drone is not flying ")
            print("Exiting the controller")
            return False  # stop listener

        self.log_update = len(drone.log)
        print(self.log_seqence, self.log_update)

        if self.log_update < self.log_seqence: #if a respond has not received after previous command
            print("Waiting for response, Sequence number for last respond: {0}".format(self.log_seqence))
        elif key == 'Z':
                if self.controller:
                    self.controller = False
                else:
                    self.controller = True
                self.log_update = self.log_seqence
                print("Contoller: ", self.controller)
        elif not self.controller:
            print("Controller is disabled: pres Z to enable")
        else:
            self.log_update = len(drone.log)
            self.log_seqence = self.log_update

            if key == 't' or key == 'T':
                print("Request for Taking off")
                self.handle_response(drone.takeoff())
            elif key == 'l' or key == 'L':
                print("Request for Landing")
                self.handle_response(drone.land())
            elif key == 'w' or key == 'W':
                print("Request for move up")
                self.handle_response(drone.up(self.distance))
            elif key == 's' or key == 'S':
                print("Request for move down")
                self.handle_response(drone.down(self.distance))
            elif key == 'a' or key == 'A':
                print("Request for yaw left")
                self.handle_response(drone.ccw(self.degree))
            elif key == 'd' or key == 'D':
                print("Request yaw right")
                self.handle_response(drone.cw(self.degree))
            elif key == '4':
                print("Request for move left")
                self.handle_response(drone.left(self.distance))
            elif key == '6':
                print("Request for move right")
                self.handle_response(drone.right(self.distance))
            elif key == '8':
                print("Request for move forward")
                self.handle_response(drone.forward(self.distance))
            elif key == '2':
                print("Request for move backward")
                self.handle_response(drone.back(self.distance))
            elif key == 'h' or key == 'H':
                print("Request for Hover the Drone")
                self.handle_response(drone.stop())
            elif key == 'e' or key == 'E':
                print("Request for Emergency")
                self.handle_response(drone.emergency())
            elif key == 'g' or key == 'G':
                print("Request for status")
                h = drone.get_height()
                b = drone.get_battery()
                t = drone.get_time()
                print("Height: {0}, Battery: {1} , Attitude: {2}".format(h,b,t))
            elif key == 'v' or key == 'V':
                print("Request for enabling video")
                self.handle_response(drone.streamon())
                # drone.video_state = True
                # drone.stream_service_on()
            elif key == 'r' or key == 'R':
                print("Request for setting video resolution")
                res = int(input("Enter resolution; 480 or 720:"))
                self.handle_response(drone.set_resolution(res)) # 480 or 720 only
                self.log_update += 1
            elif key == 'f' or key == 'F':
                print("Request for setting video fps")
                fps = int(input("Enter fps; 5, 15 or 30:"))
                self.handle_response(drone.set_fps(fps)) # 5, 15, 30 only
                self.log_update += 1
            elif key == 'i' or key == 'I':
                print("Identifying Animals")
                drone.identify_animal()
            elif key == 'c' or key == 'C':
                print("Identifying Colors")
                drone.identify_color()
            else:
                print("Invalid command : "+ key)


    def handle_response(self, res):
        try:
            print(str(res))
            print(str(res)[-6:])
        except Exception as err:
            print("Error: {0}".format(err))

    def keyboard_listner(self):
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()  # start to listen on a separate thread
        listener.join()


if __name__ == '__main__':
    drone = tello.Tello()
    controller = DroneController(drone)
    while True:
        key = input("Enter next command : ")
        controller.on_press(key)
        if key == 'exit':
            break


