import json, time
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

out = Path(__file__).resolve().parent
rclpy.init()
node = rclpy.create_node('table_instance_snapshot')
frames = []
sub = node.create_subscription(Image, '/camera/color/image_raw', lambda msg: frames.append(msg), qos_profile_sensor_data)
deadline = time.monotonic() + 45
while len(frames) < 15 and time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.5)
if not frames:
    raise RuntimeError('No camera frame received within 45 seconds')
msg = frames[-1]
bgr = CvBridge().imgmsg_to_cv2(msg, desired_encoding='bgr8')
node.destroy_node()
rclpy.shutdown()
cv2.imwrite(str(out / 'raw.png'), bgr)
model = YOLO('/home/rob/robot_grasp_table/src/yolo_vision/yolo26n-seg_openvino_model', task='segment')
result = model.predict(bgr, conf=0.25, imgsz=512, device='intel:cpu', retina_masks=True, rect=False, verbose=True)[0]
canvas = bgr.copy()
records = []
colors = [(45,190,255),(255,100,70),(80,220,100),(220,70,220),(50,220,220),(200,160,50)]
order = sorted(range(len(result.boxes)), key=lambda i: -float(result.boxes.conf[i]))
for number, i in enumerate(order, 1):
    box = result.boxes[i]
    score = float(box.conf[0])
    name = result.names[int(box.cls[0])]
    xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
    mask = result.masks.data[i].cpu().numpy() > 0.5
    color = colors[(number-1) % len(colors)]
    canvas[mask] = (canvas[mask]*0.55 + np.array(color)*0.45).astype(np.uint8)
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(canvas, contours, -1, color, 2)
    cv2.imwrite(str(out / f'mask_{number:02d}_{name}.png'), mask.astype(np.uint8)*255)
    records.append(dict(id=number, class_name=name, confidence=score, bbox_xyxy=xyxy, mask_pixels=int(mask.sum())))
for rec in records:
    color = colors[(rec['id']-1) % len(colors)]
    x1,y1,x2,y2 = rec['bbox_xyxy']
    label = f"#{rec['id']} {rec['class_name']} {rec['confidence']:.3f}"
    (tw,th),baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    x = max(0,min(x1,canvas.shape[1]-tw-8)); y = max(th+12,y1)
    cv2.rectangle(canvas,(x,y-th-8),(x+tw+8,y+4),color,-1)
    cv2.putText(canvas,label,(x+4,y-2),cv2.FONT_HERSHEY_SIMPLEX,0.65,(15,15,15),2,cv2.LINE_AA)
cv2.imwrite(str(out / 'instances_confidence.png'),canvas)
summary = dict(model='YOLO26n-seg OpenVINO', confidence_threshold=0.25, image_size=[msg.width,msg.height], stamp_sec=msg.header.stamp.sec, stamp_nanosec=msg.header.stamp.nanosec, instances=records)
(out/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
