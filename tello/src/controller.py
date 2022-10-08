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
        if key == keyboard.Key.esc:
            if drone.get_height()>0:
                print("Requesting to Land")
                drone.land()
            else:
                print(" Drone is not flying ")
            print("Exiting the controller")
            return False  # stop listener
        try:
            k = key.char  # single-char keys
        except:
            k = key.name  # other keys

        self.log_update = len(drone.log)
        print(self.log_seqence, self.log_update)

        if self.log_update < self.log_seqence: #if a respond has not received after previous command
            print("Waiting for response, Sequence number for last respond: {0}".format(self.log_seqence))
        elif k == 'Z':
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

            if k == 't' or k == 'T':
                print("Request for Taking off")
                self.handle_response(drone.takeoff())
            elif k == 'l' or k == 'L':
                print("Request for Landing")
                self.handle_response(drone.land())
            elif k == 'w' or k == 'W':
                print("Request for move up")
                self.handle_response(drone.up(self.distance))
            elif k == 's' or k == 'S':
                print("Request for move down")
                self.handle_response(drone.down(self.distance))
            elif k == 'a' or k == 'A':
                print("Request for yaw left")
                self.handle_response(drone.ccw(self.degree))
            elif k == 'd' or k == 'D':
                print("Request yaw right")
                self.handle_response(drone.cw(self.degree))
            elif k == 'left':
                print("Request for move left")
                self.handle_response(drone.left(self.distance))
            elif k == 'right':
                print("Request for move right")
                self.handle_response(drone.right(self.distance))
            elif k == 'up':
                print("Request for move forward")
                self.handle_response(drone.forward(self.distance))
            elif k == 'down':
                print("Request for move backward")
                self.handle_response(drone.back(self.distance))
            elif k == 'h' or k == 'H':
                print("Request for Hover the Drone")
                self.handle_response(drone.stop())
            elif k == 'e' or k == 'E':
                print("Request for Emergency")
                self.handle_response(drone.emergency())
            elif k == 'g' or k == 'G':
                print("Request for status")
                h = drone.get_height()
                b = drone.get_battery()
                t = drone.get_time()
                print("Height: {0}, Battery: {1} , Attitude: {2}".format(h,b,t))
            elif k == 'v' or k == 'V':
                print("Request for enabling video")
                self.handle_response(drone.streamon())
                # drone.video_state = True
                # drone.stream_service_on()
            elif k == 'r' or k == 'R':
                print("Request for setting video resolution")
                res = int(input("Enter resolution; 480 or 720:"))
                self.handle_response(drone.set_resolution(res)) # 480 or 720 only
                self.log_update += 1
            elif k == 'f' or k == 'F':
                print("Request for setting video fps")
                fps = int(input("Enter fps; 5, 15 or 30:"))
                self.handle_response(drone.set_fps(fps)) # 5, 15, 30 only
                self.log_update += 1
            elif k == 'i' or k == 'I':
                print("Identifying Animals")
                drone.identify_animal()
            elif k == 'c' or k == 'C':
                print("Identifying Colors")
                drone.identify_color()
            else:
                print("Invalid command : "+ k)


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

    def start(self):
        self.keyboard_listner()

if __name__ == '__main__':
    drone = tello.Tello()
    controller = DroneController(drone)
    controller.start()


