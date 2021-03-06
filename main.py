import datetime, time, cv2, multiprocessing
import logging as log
import paho.mqtt.publish as publish
import config


def runMultiprocessing(camera):
    try:
        logging = log.getLogger('motionkit')
        logging.setLevel(log.INFO)
        # logging is a singleton, make sure we don't duplicate the handlers and spawn additional log messages
        if not logging.handlers:
            logHandler = log.StreamHandler()
            logHandler.setLevel(log.INFO)
            logHandler.setFormatter(
                log.Formatter("%(camera)s - {%(pathname)s:%(lineno)d} %(asctime)s - %(levelname)s - %(message)s",
                              '%m/%d/%Y %I:%M:%S %p'))
            logging.addHandler(logHandler)
            logging = log.LoggerAdapter(logging, {"camera": camera['name']})

        # https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
        # https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/

        avg = None
        fps = None
        # sometimes the cameras gives wildy off FPS values so we continually retry until we get something reasonable
        while fps is None or fps <= 0 or fps > 120:
            vs = cv2.VideoCapture(camera['url'])
            fps = float(vs.get(cv2.CAP_PROP_FPS))

        logging.info(f"Resolution: {vs.get(cv2.CAP_PROP_FRAME_WIDTH)} x {vs.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        logging.info(f"{fps} FPS")
    except Exception as e:
        logging.error(e)


    # loop over the frames of the video
    last_motion = False
    while True:
        try:
            start_time = datetime.datetime.now()
            # returns a tuple, first element is a bool
            _, frame = vs.read()
            frame = frame[469:753, 883:1234]
            if frame is not None:
                # convert it to grayscale, and blur it
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if avg is None:
                    avg = gray.copy().astype("float")
                    continue

                # accumulate the weighted average between the current frame and
                # previous frames, then compute the difference between the current
                # frame and running average
                cv2.accumulateWeighted(gray, avg, 0.5)
                frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

                # threshold the delta image, dilate the thresholded image to fill
                # in holes, then find contours on thresholded image
                thresh = cv2.threshold(frameDelta, int(config.delta_threshold), 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)

                # cv2.RETR_EXTERNAL - retrieves only the extreme outer contours
                cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                motion = False
                for c in cnts:
                    x, y, w, h = cv2.boundingRect(c)
                    # if it doesn't hit our size cutoff, skip it
                    if w < vs.get(cv2.CAP_PROP_FRAME_WIDTH) * config.contour_size_cutoff_percentage or h < vs.get(
                            cv2.CAP_PROP_FRAME_HEIGHT) * config.contour_size_cutoff_percentage:
                        continue
                    # BGR - blue, green, red
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 1)
                    motion = True

                #cv2.imshow('test', frame)
                #cv2.waitKey(1)

                if motion != last_motion:
                    last_motion = motion
                    if motion:
                        logging.info("Motion detected")
                        # http://www.steves-internet-guide.com/understanding-mqtt-qos-levels-part-1/
                        # http://www.steves-internet-guide.com/understanding-mqtt-qos-2/
                        # QOS 0 - Once (not guaranteed)
                        # QOS 1 - At Least Once (guaranteed)
                        # QOS 2 - Only Once (guaranteed)
                        #mqttclient.publish("cammotion/" + camera['name'], payload=cv2.imencode('.png', frame)[1].tobytes(), qos=0)
                        # case sensitive? make sure to use "ON" not "on"
                        publish.single("cammotion/" + camera['name'] + "/state", payload="ON", qos=1, hostname=str(config.mqtt_ip), port=int(config.mqtt_port))
                    else:
                        logging.info("Motion end")
                        publish.single("cammotion/" + camera['name'] + "/state", payload="OFF", qos=1, hostname=str(config.mqtt_ip), port=int(config.mqtt_port))

            time_delta = (datetime.datetime.now() - start_time).total_seconds() * 1000  # milliseconds

            #if time_delta > 0 and float(1000 / time_delta) < float(vs.get(cv2.CAP_PROP_FPS)) * 0.8:
             #   logging.warning(f"Running at {1000 / time_delta} FPS, target is {vs.get(cv2.CAP_PROP_FPS)} FPS")
              #  logging.warning("Not hitting the target FPS, consider reducing camera FPS or improving hardware.")
        except Exception as e:
            logging.error(e)
            time.sleep(1)  # one second
            vs = cv2.VideoCapture(camera['url'])


if __name__ == '__main__':
    for camera in config.cameras:
        p = multiprocessing.Process(target=runMultiprocessing, args=(camera,))
        p.start()
