from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Path, Body, Query, File
from fastapi.responses import FileResponse
from PIL import Image, ImageFilter
import ssl
import os
from starlette.background import BackgroundTasks
import urllib.request, urllib.parse
import cv2 as cv
import numpy as np
from tqdm import tqdm


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
    image_url = "https://cmp.photoprintit.com/api/photos/" + imgId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"

    urllib.request.urlretrieve(image_url, img_path)

    blurImage = Image.open(img_path)
    # Here I use the Pillow library to apply a simple box blur on the fetched image, alternatively OpenCV can be used
    # instead of Pillow
    blurImage = blurImage.filter(ImageFilter.BoxBlur(10))
    blurImage.save(img_path)

    # The background task runs after the File is returned completetly
    background_tasks.add_task(remove_file, img_path)
    return FileResponse(img_path)


@app.get("/get-background-image/{cldId}/{videoId}/{backgroundImageOption}")
async def get_background_image(cldId, videoId, backgroundImageOption, background_tasks: BackgroundTasks):
    if backgroundImageOption == "MOG2":
        background_subtraction = cv.createBackgroundSubtractorMOG2()
    else:
        background_subtraction = cv.createBackgroundSubtractorKNN()

    video_url = "https://cmp.photoprintit.com/api/photos/" + videoId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"
    # pull video from server to specified video path
    video_path = 'app/bib/' + videoId + ".mp4"
    urllib.request.urlretrieve(video_url, video_path)

    # read input video
    video = cv.VideoCapture(cv.samples.findFileOrKeep(video_path))
    # feed video into background subtraction
    while True:
        ret, frame = video.read()
        if frame is None:
            break

        background_subtraction.apply(frame)

    # save background image to specified image path
    bg_image = background_subtraction.getBackgroundImage()
    bg_mask_image_path = 'app/bib/bg_mask_' + videoId + '.png'
    cv.imwrite(bg_mask_image_path, bg_image)

    background_tasks.add_task(remove_file, video_path)
    return FileResponse(bg_mask_image_path)


@app.get("/get-foreground-mask/{cldId}/{videoId}/{foregroundMaskOption}")
async def get_foreground_mask(cldId, videoId, foregroundMaskOption, background_tasks: BackgroundTasks):
    if foregroundMaskOption == "MOG2":
        background_subtraction = cv.createBackgroundSubtractorMOG2()
    else:
        background_subtraction = cv.createBackgroundSubtractorKNN()

    video_url = "https://cmp.photoprintit.com/api/photos/" + videoId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"
    # pull video from server to specified video path
    video_path = 'app/bib/' + videoId + ".mp4"
    urllib.request.urlretrieve(video_url, video_path)

    # read input video
    video = cv.VideoCapture(cv.samples.findFileOrKeep(video_path))
    # feed video into background subtraction
    while True:
        ret, frame = video.read()
        if frame is None:
            break

        fg_mask = background_subtraction.apply(frame)

    # save foreground mask to specified image path
    fg_mask_image_path = 'app/bib/fg_mask_' + videoId + '.png'
    cv.imwrite(fg_mask_image_path, fg_mask)

    background_tasks.add_task(remove_file, video_path)
    return FileResponse(fg_mask_image_path)


@app.get("/get-edge-detection/{cldId}/{videoId}")
async def get_edge_detection(cldId, videoId, background_tasks: BackgroundTasks):
    video_url = "https://cmp.photoprintit.com/api/photos/" + videoId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"
    # pull video from server to specified video path
    video_path = 'app/bib/' + videoId + ".mp4"
    urllib.request.urlretrieve(video_url, video_path)

    # read input video
    video = cv.VideoCapture(cv.samples.findFileOrKeep(video_path))
    # feed video into background subtraction
    while True:
        ret, frame = video.read()
        if frame is None:
            break

        sigma = 0.3
        median = np.median(frame)
        lower = int(max(0, (1.0 - sigma) * median))
        upper = int(min(255, (1.0 + sigma) * median))
        edges = cv.Canny(frame, lower, upper)

    # save foreground mask to specified image path
    edge_image_path = 'app/bib/edges_' + videoId + '.png'
    cv.imwrite(edge_image_path, edges)

    background_tasks.add_task(remove_file, video_path)
    return FileResponse(edge_image_path)


@app.get("/get-long-exposure/{cldId}/{videoId}")
async def get_long_exposure(cldId, videoId, background_tasks: BackgroundTasks):
    video_url = "https://cmp.photoprintit.com/api/photos/" + videoId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"
    # pull video from server to specified video path
    video_path = 'app/bib/' + videoId + ".mp4"
    urllib.request.urlretrieve(video_url, video_path)

    # read input video
    video = cv.VideoCapture(cv.samples.findFileOrKeep(video_path))

    step = 1
    r, g, b = None, None, None
    r_avg, g_avg, b_avg = averager(),averager(), averager()
    # Get the total frames to be used by the progress bar
    total_frames = int(video.get(cv.CAP_PROP_FRAME_COUNT))
    for count in tqdm(range(total_frames)):
        # Split the frame into its respective channels
        _, frame = video.read()

        if count % step == 0 and frame is not None:
            # Get the current RGB
            b_curr, g_curr, r_curr = cv.split(frame.astype("float"))
            r, g, b = r_avg(r_curr), g_avg(g_curr), b_avg(b_curr)

    # Merge the RGB averages together and write the output image to disk
    avg = cv.merge([b, g, r]).astype("uint8")

    # save foreground mask to specified image path
    long_exposure_image_path = 'app/bib/edges_' + videoId + '.jpg'
    cv.imwrite(long_exposure_image_path, avg)

    background_tasks.add_task(remove_file, video_path)
    return FileResponse(long_exposure_image_path)


@app.get("/get-freeze-me/{cldId}/{videoId}")
async def get_freeze_me(cldId, videoId, background_tasks: BackgroundTasks):
    video_url = "https://cmp.photoprintit.com/api/photos/" + videoId + ".org?size=original&errorImage=false&cldId=" + cldId + "&clientVersion=0.0.0-uni_webapp_demo"
    # pull video from server to specified video path
    video_path = 'app/bib/' + videoId + ".mp4"
    urllib.request.urlretrieve(video_url, video_path)

    # %% Generate Long Exposure
    video = cv.VideoCapture(cv.samples.findFileOrKeep(video_path))
    step = 1
    r, g, b = None, None, None
    r_avg, g_avg, b_avg = averager(), averager(), averager()
    # Get the total frames to be used by the progress bar
    total_frames = int(video.get(cv.CAP_PROP_FRAME_COUNT))
    for count in tqdm(range(total_frames)):
        # Split the frame into its respective channels
        _, frame = video.read()

        if count % step == 0 and frame is not None:
            # Get the current RGB
            b_curr, g_curr, r_curr = cv.split(frame.astype("float"))
            r, g, b = r_avg(r_curr), g_avg(g_curr), b_avg(b_curr)

    # Merge the RGB averages together and write the output image to disk
    long_exposure = cv.merge([b, g, r]).astype("uint8")
    long_exposure_path = 'long_exposure_path.jpg'
    cv.imwrite(long_exposure_path, long_exposure)

    # %% Get last frame and write to file
    video = cv.VideoCapture(cv.samples.findFileOrKeep(video_path))
    while True:
        ret, frame = video.read()
        if frame is None:
            break
        else:
            last_frame = frame
    last_frame_path = 'last_frame_path.jpg'
    cv.imwrite(last_frame_path, last_frame)

    # %% Generate grab cut mask from last frame and write to file
    last_frame = cv.imread(last_frame_path)
    # apply grabcut to detect object and write to file
    mask = np.zeros(last_frame.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (800, 600, 500, 450)  # (startx, starty, offsetx, offsety)
    (mask, bgdModel, fgdModel) = cv.grabCut(last_frame, mask, rect, bgdModel, fgdModel, 5, cv.GC_INIT_WITH_RECT)
    grab_cut_processed = last_frame * mask[:, :, np.newaxis]
    grab_cut_processed_path = 'grab_cut_processed_path.jpg'
    cv.imwrite(grab_cut_processed_path, grab_cut_processed)
    # apply threshold to generate mask and write to file
    grab_cut_processed = cv.imread(grab_cut_processed_path, cv.IMREAD_GRAYSCALE)
    ret, grab_cut_mask = cv.threshold(grab_cut_processed, 5, 255, cv.THRESH_BINARY)
    grab_cut_mask_path = 'grab_cut_mask_path.jpg'
    cv.imwrite(grab_cut_mask_path, grab_cut_mask)

    # %% Merge last frame into long exposure at mask points
    long_exposure = cv.imread(long_exposure_path)
    last_frame = cv.imread(last_frame_path)
    grab_cut_mask = cv.imread(grab_cut_mask_path)
    freeze_me_image = long_exposure.copy()
    freeze_me_image[np.where(grab_cut_mask == 255)] = last_frame[np.where(grab_cut_mask == 255)]
    freeze_me_path = 'freeze_me_path.jpg'
    cv.imwrite(freeze_me_path, freeze_me_image)

    background_tasks.add_task(remove_file, video_path)
    background_tasks.add_task(remove_file, long_exposure_path)
    background_tasks.add_task(remove_file, last_frame_path)
    background_tasks.add_task(remove_file, grab_cut_processed_path)
    background_tasks.add_task(remove_file, grab_cut_mask_path)
    return FileResponse(freeze_me_path)


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



# Delete a file
def remove_file(path: str) -> None:
    os.unlink(path)