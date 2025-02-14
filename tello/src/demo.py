from tello import tello


drone = tello.Tello()

# 起飞
drone.takeoff()

# 前进100cm
drone.forward(20)

# 旋转90°
drone.cw(30)

# 左翻滚
#drone.flip('l')

# 打开视频流
drone.streamon()

# 降落
drone.land()
