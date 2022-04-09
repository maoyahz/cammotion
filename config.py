mqtt_ip = "192.168.1.5"
mqtt_port = "1883"
# threshold value by which we identify differences in the delta frame
delta_threshold = 5
# Minimum percentage of the screen width or height that we need to find contour motion
# in order to trigger detection. Decrease to identify more events as motion or to identify
# things that are farther away.  Increase to require more of the overall image to be within
# the frame or closer to identify motion.
# value is greater than 0 and less than 1
contour_size_cutoff_percentage = 0.03

cameras = [
    {
    "name": "water",
    "url": "rtsp://admin:123456@192.168.1.123:554/Streaming/Channels/1"
    }
]
