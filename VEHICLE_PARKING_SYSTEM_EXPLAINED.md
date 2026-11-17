# Vehicle Parking Management System – How It Works

This project is a smart vehicle parking monitoring system that combines a Flask web app with computer vision and object tracking. It lets a user:

- Register or log in
- Upload a parking-lot video
- Select a parking layout (for example, `carpark_1` or `carpark_2`)
- Detect vehicles in the video
- Track each vehicle across frames
- Check whether the vehicle is inside a marked parking spot
- Show occupied vs. available parking spaces

In short: the system watches a video, recognizes vehicles, tracks them over time, and marks which parking spaces are full.

---

## 1. Overall architecture

The project is made of a few main parts:

1. Flask web interface
   - Handles login, registration, contact form, and model page
   - Runs the web backend using `flask_inference.py`

2. YOLO object detection
   - Detects vehicles such as cars in each video frame
   - Uses the model file `yolov11n_visdrone_model.pt`

3. SORT tracking
   - Tracks detected cars between frames so the same car keeps the same ID
   - Implemented in `sort.py`

4. Parking-space polygons
   - Each parking slot is defined as a polygon in `car_parking_coordinate_data.py`
   - A vehicle is considered inside a slot if its center point lies inside the polygon

5. User data storage
   - User accounts are saved in `users.json`
   - Contact submissions are stored in `contact_data.json`

---

## 2. Main backend file: `flask_inference.py`

This is the main application file. It starts the Flask server and defines all routes.

### 2.1 Flask app setup

```python
app = Flask(__name__)
CORS(app)
app.secret_key = "a"
```

- `Flask(__name__)` creates the web app.
- `CORS(app)` allows cross-origin requests if needed by the browser.
- `app.secret_key` is used by Flask sessions to manage login state.

This is a demo app, so the secret is hardcoded and not production-grade.

### 2.2 JSON storage helpers

```python
def load_users():
    try:
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
```

This loads the user dictionary from `users.json`.

```python
def save_users(users):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(users, file, indent=4)
```

This writes updated user info back to the file.

This makes the app simple and file-based instead of using a database.

---

## 3. Web routes and page flow

The app defines routes like these:

```python
@app.route("/", methods=["GET", "POST"])
def project():
    return render_template("index.html")
```

```python
@app.route("/login")
def login():
    return render_template("login.html")
```

```python
@app.route("/register")
def register():
    return render_template("register.html")
```

```python
@app.route("/model")
def model():
    return render_template("model.html")
```

### Role of each page

- `/` → homepage
- `/login` → login page
- `/register` → registration form
- `/model` → video upload and prediction screen
- `/about` → about page

These pages are rendered from the `templates/` folder using Flask’s `render_template` function.

---

## 4. User registration and login

### 4.1 Register route

```python
@app.route("/reg", methods=["POST", "GET"])
def signup():
    msg = ""
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        users = load_users()

        if email in users:
            return render_template("login.html", error=True)
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            msg = "Invalid email address"
        else:
            users[email] = {"name": name, "password": password}
            save_users(users)
            msg = "Account created successfully"
    return render_template("login.html", msg=msg)
```

What this does:

- Reads the form data from the registration page
- Checks whether a user already exists with that email
- Validates the email format with a regex
- Saves the user into `users.json`

### 4.2 Login route

```python
@app.route("/log", methods=["POST", "GET"])
def login1():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        users = load_users()

        user = users.get(email)
        if user and user["password"] == password:
            session["Loggedin"] = True
            session["id"] = email
            session["email"] = email
            return render_template("model.html")
        else:
            msg = "Incorrect Email / Password"
            return render_template("login.html", msg=msg)
    else:
        return render_template("login.html")
```

This verifies credentials by:

- Reading email and password from the login form
- Loading users from `users.json`
- Matching the email and password
- If correct, storing session variables: `Loggedin`, `id`, and `email`
- Redirecting the user to the model page

This is a simple session-based login, not a secure authentication system.

---

## 5. Contact form handling

```python
@app.route("/submit_contact", methods=["POST"])
def submit_contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    contact_entry = {"name": name, "email": email, "message": message}

    try:
        with open(JSON_FILE, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []

    data.append(contact_entry)

    with open(JSON_FILE, "w") as file:
        json.dump(data, file, indent=4)

    return jsonify({"status": "success", "message": "Contact details saved!"}), 200
```

The app stores contact messages in `contact_data.json`. This is effectively a tiny contact database stored in JSON.

---

## 6. The prediction route: `/predict`

This is the most important part of the system.

```python
@app.route("/predict", methods=["POST"])
def predict():
    if 'video_file' not in request.files:
        return jsonify({"error": "Video file and polygon file are required"}), 400

    video_file = request.files['video_file']
    video_path = f"Media/{video_file.filename}"
    video_file.save(video_path)
```

### What happens here?

- The browser sends the uploaded video file and selected parking lot option
- The backend checks that a file exists
- It saves the uploaded video into the `Media/` folder
- Then it loads the saved file using OpenCV

```python
cap = cv2.VideoCapture(video_path)
polygon_option = request.form.get('polygon_option')
```

The selected parking layout is used to define the actual parking slot polygons.

---

## 7. Loading the detection model

```python
classnames = []
with open('classes.txt', 'r') as f:
    classnames = f.read().splitlines()

model = YOLO('yolov11n_visdrone_model.pt')
parking_polygons = car_park_coordinate(polygon_option)
```

### Why this matters

- `classes.txt` stores class names like `car`, `truck`, etc.
- `YOLO(...)` loads the object detection model
- `car_park_coordinate(...)` loads the coordinates for the selected parking layout

This means the detector knows what objects to recognize and the app knows which areas of the frame are parking spaces.

---

## 8. Parking slot definition with polygons

The parking spots are not stored as rectangles only—they are polygons.

The file `car_parking_coordinate_data.py` contains data like:

```python
parking_coordinates = {
    "carpark_1": [
        np.array([[143, 323], [210, 439], [126, 456], [50, 345]]),
        np.array([[224, 320], [319, 439], [257, 461], [156, 336]]),
        ...
    ],
    "carpark_2": [
        np.array([[160, 85], [158, 133], [29, 135], [31, 87]]),
        ...
    ]
}
```

### Why polygons?

A real parking slot is not always a perfect rectangle. Since the camera may be angled, polygon-based slot boundaries are more accurate than simple boxes.

The function returns the chosen list of polygons:

```python
def car_park_coordinate(input):
    return parking_coordinates[input]
```

This allows each parking-lot video to have a custom set of coordinates.

---

## 9. Checking whether a vehicle is inside a parking spot

The app defines this helper:

```python
def is_parking_space_occupied(box_mid, parking_polygons):
    for idx, polygon in enumerate(parking_polygons):
        if cv2.pointPolygonTest(polygon, box_mid, False) >= 0:
            return idx
    return None
```

### What it does

- Takes the centroid (midpoint) of the detected object
- Checks whether that point lies inside one of the parking polygons
- If yes, returns the index of that parking slot

This is the core logic for occupancy detection.

`cv2.pointPolygonTest()` is a very important OpenCV function here:

- It tells us whether a point is inside a polygon
- If the center of a detected car falls inside a parking slot polygon, that slot is considered occupied

---

## 10. Object detection using YOLO

Inside the video-processing loop:

```python
results = model(frame, stream=1)
```

This runs the YOLO model on the current frame and returns detection results.

Then the code loops through each result:

```python
for info in results:
    boxes = info.boxes
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0]
        conf = box.conf[0]
        classindex = box.cls[0].item()
        object_detected = classnames[int(classindex)]

        if object_detected == 'car':
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            new_detections = np.array([x1, y1, x2, y2, conf])
            detections = np.vstack((detections, new_detections))
```

### Explanation

- `box.xyxy[0]` gives the bounding box coordinates in the form `[x1, y1, x2, y2]`
- `box.conf[0]` is the confidence score
- `box.cls[0]` is the detected class index
- `classnames[...]` converts that index into a human-readable label like `car`
- It only keeps detected objects whose label is `car`

This is a very practical choice: the project is looking specifically at cars and ignoring people, buses, or trucks.

---

## 11. Tracking vehicles with SORT

The system has this line:

```python
tracker = Sort(max_age=30)
```

The tracker is created from `sort.py`, which is an implementation of the SORT (Simple Online and Realtime Tracking) algorithm.

### Why tracking matters

Detection alone gives us a car’s position only for one frame. But parking occupancy needs to know whether a car is still in a slot across several frames. Without tracking, a car could appear as a new object every frame.

SORT solves this by:

- Predicting the next position of an existing object
- Comparing it with new detections using IoU (Intersection over Union)
- Matching the right detection to the right tracked object
- Assigning a stable object ID

Then:

```python
track_result = tracker.update(detections)
```

This returns tracked objects as an array:

```python
[x1, y1, x2, y2, obj_id]
```

Now the app can repeatedly draw and inspect the same vehicles.

---

## 12. How `sort.py` works internally

This file is the tracking engine. It is not a Flask app—it is a detection-tracking algorithm.

### 12.1 `linear_assignment`

```python
def linear_assignment(cost_matrix):
    try:
        import lap
        _, x, y = lap.lapjv(cost_matrix, extend_cost=True)
        return np.array([[y[i],i] for i in x if i >= 0])
    except ImportError:
        from scipy.optimize import linear_sum_assignment
        x, y = linear_sum_assignment(cost_matrix)
        return np.array(list(zip(x, y)))
```

This solves the matching problem between tracks and detections using a minimum-cost assignment algorithm.

This is critical because when many cars are detected at once, the system must decide which existing track belongs to which new detection.

### 12.2 `iou_batch`

```python
def iou_batch(bb_test, bb_gt):
    ...
```

This computes Intersection over Union between bounding boxes.

The formula is:

- overlap area / union area

It is used to decide how similar a predicted object position is to a newly detected one.

### 12.3 `convert_bbox_to_z`

```python
def convert_bbox_to_z(bbox):
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w/2.
    y = bbox[1] + h/2.
    s = w * h
    r = w / float(h)
    return np.array([x, y, s, r]).reshape((4, 1))
```

This converts a bounding box into a state vector used by the Kalman filter:

- x, y = center point
- s = area
- r = aspect ratio

This is the representation used by the tracker.

### 12.4 `convert_x_to_bbox`

This converts the filtered state back into a bounding box.

```python
def convert_x_to_bbox(x,score=None):
    w = np.sqrt(x[2] * x[3])
    h = x[2] / w
    ...
    return np.array([x[0]-w/2., x[1]-h/2., x[0]+w/2., x[1]+h/2.]).reshape((1,4))
```

This is reverse engineering: the tracker predicts a box and then reconstructs it in rectangle format for drawing and matching.

### 12.5 `KalmanBoxTracker`

This class keeps track of a single object’s hidden state.

```python
self.kf = KalmanFilter(dim_x=7, dim_z=4)
```

A Kalman filter predicts where an object is likely to move next.

It stores:

- current position
- velocity estimates
- age of track
- hit streak count
- update history

It also maintains a unique object ID.

```python
self.id = KalmanBoxTracker.count
KalmanBoxTracker.count += 1
```

Each tracked object gets a unique integer ID.

### 12.6 `associate_detections_to_trackers`

This function matches current detections to existing tracked objects using IoU and assignment logic.

```python
matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(dets, trks, self.iou_threshold)
```

It decides:

- which detection matches which tracker
- which detections are new objects
- which trackers disappeared and should be dropped

### 12.7 `Sort.update()`

This is the main tracking loop.

```python
for t, trk in enumerate(trks):
    pos = self.trackers[t].predict()[0]
    trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
```

It predicts the next position of each known object before matching with new detections.

Then:

```python
matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(dets, trks, self.iou_threshold)
```

It matches detections to predictions.

Then:

```python
for m in matched:
    self.trackers[m[1]].update(dets[m[0], :])
```

This updates the internal state of already-tracked cars.

New objects get their own tracker:

```python
for i in unmatched_dets:
    trk = KalmanBoxTracker(dets[i,:])
    self.trackers.append(trk)
```

And finally it returns tracked output with IDs:

```python
ret.append(np.concatenate((d,[trk.id+1])).reshape(1,-1))
```

It adds `+1` because the MOT benchmark expects positive IDs.

---

## 13. Occupancy detection loop in `flask_inference.py`

After tracking, the app processes each result:

```python
for result in track_result:
    x1, y1, x2, y2, obj_id = map(int, result)
    box_mid = ((x1 + x2) // 2, (y1 + y2) // 2)
    occupied_space_idx = is_parking_space_occupied(box_mid, parking_polygons)
```

Here:

- `track_result` gives each tracked vehicle with a bounding box and ID
- `box_mid` is the center point of the vehicle
- If the center point falls inside a parking polygon, then that parking slot is counted as occupied

```python
if occupied_space_idx is not None:
    occupied_spaces.add(occupied_space_idx)
```

This set stores all occupied parking-slot indices for the current frame.

Since `occupied_spaces` is a set, each parking slot is only stored once even if multiple vehicles appear in the same slot.

---

## 14. Drawing the parking area on the video

```python
for idx, polygon in enumerate(parking_polygons):
    color = (0, 255, 0) if idx not in occupied_spaces else (0, 0, 255)
    cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)
```

### Meaning

- Green lines = free spot
- Red lines = occupied spot

Then the code draws device boxes around vehicles:

```python
cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
cvzone.putTextRect(frame, f'ID: {obj_id}', [x1 + 5, y1 - 10], thickness=1, scale=1.2)
```

This marks the vehicles visually and labels them with their tracker ID.

---

## 15. Counting available and occupied slots

```python
total_spaces = len(parking_polygons)
occupied_count = len(occupied_spaces)
available_count = total_spaces - occupied_count
```

Then it displays them on the frame:

```python
cvzone.putTextRect(frame, f'Total Spaces = {total_spaces}', [20, 40], thickness=2, scale=1.5, border=2)
cvzone.putTextRect(frame, f'Occupied = {occupied_count}', [20, 80], thickness=2, scale=1.5, border=2)
cvzone.putTextRect(frame, f'Available = {available_count}', [20, 120], thickness=2, scale=1.5, border=2)
```

So the live video window shows:

- Total number of parking spaces
- Number currently occupied
- Number currently available

This is the visible output of the smart parking system.

---

## 16. Video display loop

```python
cv2.imshow('Smart Parking Occupancy', cv2.resize(frame, (1020, 500)))
if cv2.waitKey(1) & 0xFF == ord('q'):
    break
```

This displays each processed frame in a window named `Smart Parking Occupancy`.

- Press `q` to quit the video window
- The loop continues until the video ends or the user stops it

Finally:

```python
cap.release()
cv2.destroyAllWindows()
```

This closes the camera/video stream cleanly.

---

## 17. Frontend form interaction

The HTML page `templates/model.html` contains the upload form:

```html
<form id="uploadForm">
    <input type="file" id="videoUpload" name="video_file">
    <select id="polygonSelect" name="polygon_option">
        <option value="carpark_1">Carpark 1</option>
        <option value="carpark_2">Carpark 2</option>
        <option value="carpark_3">Carpark 3</option>
    </select>
    <button type="button" onclick="uploadAndPredict()">Submit and Predict</button>
</form>
```

Then JavaScript sends a `FormData` request to the backend:

```javascript
const formData = new FormData();
formData.append("video_file", videoInput.files[0]);
formData.append("polygon_option", polygonSelect.value);

fetch('http://localhost:5000/predict', {
    method: 'POST',
    body: formData
})
```

This is how the browser uploads the video and selected parking layout to Flask.

---

## 18. Step-by-step workflow of the system

Here is the full process in simple order:

1. User registers or logs in
2. User opens the model page
3. User uploads a parking video
4. User chooses the parking layout such as `carpark_1`
5. Flask saves the video to `Media/`
6. OpenCV loads the video frame by frame
7. YOLO detects cars in each frame
8. SORT tracks each vehicle using object IDs
9. The center point of each vehicle is checked against parking polygons
10. If the center falls inside a polygon, that slot is marked occupied
11. The frame is drawn with green/red parking slots
12. Occupied/available counts are displayed
13. The live output window shows the smart parking status

---

## 19. What makes this system work

The project combines four basic ideas:

- Computer vision: detecting cars in images/video
- Tracking: following each car across frames
- Geometric mapping: defining parking spaces as polygons
- Web application: letting the user upload videos and choose layouts

That combination turns a camera feed into a live parking occupancy monitor.

---

## 20. Important notes and limitations

This project is a good demonstration, but it is not a full production system.

### Limitations

- It uses file-based storage instead of a real database
- Login is simple and not secure for real production use
- The code uses a hardcoded Flask secret key
- It looks only for cars, not trucks or other vehicles unless modified
- The project may expect certain camera angles or parking-lot layouts
- The selected parking option `carpark_3` appears in the UI, but the coordinate file mostly contains `carpark_1` and `carpark_2` definitions, so more layouts may need to be added

### Strong points

- Very understandable architecture
- Good mix of Flask + OpenCV + YOLO + tracking
- Suitable as an academic or prototype smart parking project

---

## 21. Summary

This system works like a smart surveillance parking system:

- a camera records the car park,
- the object detector finds vehicles,
- the tracker follows each vehicle,
- parking-slot polygons tell the system which spaces are occupied,
- the web app displays the result in real time.

So the app effectively converts a parking video into a live occupancy map and count of free parking slots.

---

This explanation is based on the code in:

- `flask_inference.py`
- `sort.py`
- `car_parking_coordinate_data.py`
- `templates/model.html`
- `classes.txt`

If you want, I can also turn this into a more formal project report with sections like:

- Introduction
- Objectives
- Methodology
- Algorithm flow
- Results
- Conclusion
- Future enhancements
