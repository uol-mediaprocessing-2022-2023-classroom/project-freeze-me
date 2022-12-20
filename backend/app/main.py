from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Path, Body, Query, File
from fastapi.responses import FileResponse
from PIL import Image, ImageFilter
import ssl
import os
from starlette.background import BackgroundTasks
import urllib.request, urllib.parse
from tqdm import tqdm
import cv2

app = FastAPI()
ssl._create_default_https_context = ssl._create_unverified_context

# List of URLs which have access to this API
origins = [
    "https://localhost:8080",
    "http://localhost:8080/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return{"Test": "test"}

# Endpoint for retrieving a blurred version of an image
# The image is fetched from the URL in the post body and a blur is applied to it, the result is returned
@app.get("/get-blur/{cldId}/{imgId}")
async def get_blur(cldId, imgId, background_tasks: BackgroundTasks):

    img_path = 'app/bib/' + imgId + ".jpg"
    image_url = "https://tcmp.photoprintit.com/api/photos/" + imgId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"

    urllib.request.urlretrieve(image_url, img_path)

    blurImage = Image.open(img_path)
    # Here I use the Pillow library to apply a simple box blur on the fetched image, alternatively OpenCV can be used
    # instead of Pillow
    blurImage = blurImage.filter(ImageFilter.BoxBlur(10))
    blurImage.save(img_path)

    # The background task runs after the File is returned completetly
    background_tasks.add_task(remove_file, img_path)
    return FileResponse(img_path)

@staticmethod
def averager():
    """Calculate the average using a clojure."""
    count = 0
    total = 0.0

    def average(value):
        nonlocal count, total
        count += 1
        total += value
        return total / count

    return average

@app.get("/get-longexp/{cldId}/{imgId}")
async def get_longexp(cldId, imgId, background_tasks: BackgroundTasks):

    img_path = 'app/bib' + imgId + ".jpg"
    video_path = 'app/bib/' + imgId + ".mp4"
    video_url = "https://tcmp.photoprintit.com/api/photos/" + imgId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"
    step = 1
    urllib.request.urlretrieve(video_url, video_path)

    # Open a pointer to the video file
    stream = cv2.VideoCapture(video_path)

    # Get the total frames to be used by the progress bar
    total_frames = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))

    r, g, b = None, None, None
    r_avg, g_avg, b_avg = averager(),averager(), averager()

    for count in tqdm(range(total_frames)):
        # Split the frame into its respective channels
        _, frame = stream.read()

        if count % step == 0 and frame is not None:
            # Get the current RGB
            b_curr, g_curr, r_curr = cv2.split(frame.astype("float"))
            r, g, b = r_avg(r_curr), g_avg(g_curr), b_avg(b_curr)

    # Merge the RGB averages together and write the output image to disk
    avg = cv2.merge([b, g, r]).astype("uint8")
    cv2.imwrite(img_path, avg)

    # Release the stream pointer
    stream.release()

    return FileResponse(img_path)

# Delete a file
def remove_file(path: str) -> None:
    os.unlink(path)