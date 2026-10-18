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
bgr = cv2.imread(str(out / 'raw.png'))
model = YOLO('/home/rob/robot_grasp_table/src/yolo_vision/yolo26n-seg_openvino_model', task='segment')
x0,y0,xend,yend = 340,380,930,610
result = model.predict(bgr[y0:yend,x0:xend], conf=0.25, agnostic_nms=True, imgsz=512, device='intel:cpu', retina_masks=True, rect=False, verbose=True)[0]
canvas = bgr.copy()
records = []
colors = [(45,190,255),(255,100,70),(80,220,100),(220,70,220),(50,220,220),(200,160,50)]
order = sorted(range(len(result.boxes)), key=lambda i: -float(result.boxes.conf[i]))
for number, i in enumerate(order, 1):
    box = result.boxes[i]
    score = float(box.conf[0])
    name = result.names[int(box.cls[0])]
    xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
    xyxy = [xyxy[0]+x0, xyxy[1]+y0, xyxy[2]+x0, xyxy[3]+y0]
    mask = np.zeros(bgr.shape[:2], dtype=bool)
    mask[y0:yend,x0:xend] = result.masks.data[i].cpu().numpy() > 0.5
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
cv2.imwrite(str(out / 'table_detail.png'), cv2.resize(canvas[340:630,330:1100], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
summary = dict(model='YOLO26n-seg OpenVINO', confidence_threshold=0.25, image_size=[bgr.shape[1],bgr.shape[0]], roi_xyxy=[x0,y0,xend,yend], source_image='raw.png', instances=records)
(out/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
