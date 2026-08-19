import asyncio
from contextlib import asynccontextmanager
from http.client import HTTPException
from pathlib import Path
from app.email_sender import EmailSender
from app.config import email_settings
from fastapi import FastAPI
from app.api.v1.routes import router as api_router
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from fastapi import Request
import socket
from app.schemas import Registration, SetRequest , Heartbeat , ESPAlert
import requests
import httpx
from fastapi.middleware.cors import CORSMiddleware




# This function runs in the background and checks the last seen time of each device in the devices dictionary. If a device has not been seen for more than the OFFLINE_THRESHOLD, it is marked as offline. Otherwise, it is marked as online. This allows us to keep track of which devices are currently online and which are offline based on their heartbeat signals.
async def monitor_devices():
    while True:
        now = datetime.now(timezone.utc)

        # print("Monitor devices check is running now")


        if(len(devices)>0):
            for device_id, device in devices.items():
                if now - device["last_seen"] > OFFLINE_THRESHOLD:
                    if "online" in device and device["online"]:
                        # print that the device is offline
                        print(f"Device {device_id} is offline. Last seen at {device['last_seen']}")
                    device["online"] = False
                else:
                    device["online"] = True


        await asyncio.sleep(3)  # check every 3 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    # declare the devices dictionary as global to be used in the monitor_devices function
    # Start the device monitoring task
    # print("Starting the app")
    asyncio.create_task(monitor_devices())
    yield


app = FastAPI(title="FPI Boilerplate", version="0.1.0" , lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    # Also allow the Vite dev server when it's opened from another device on
    # the same LAN/hotspot (e.g. http://10.240.147.22:5173), not just localhost.
    allow_origin_regex=r"http://(127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}):5173",
    allow_methods=["*"],
    allow_headers=["*"],
)

devices = {}

# Threshold for considering a device offline if it hasn't sent a heartbeat in the last X minutes. This can be adjusted based on the expected frequency of heartbeats from the devices.
OFFLINE_THRESHOLD = timedelta(seconds=120) # 2 minutes



@app.get("/")
async def root():
    hostname = socket.gethostname()
    server_internal_ip = socket.gethostbyname(hostname)
    print(f"Server internal IP: {server_internal_ip}")
    return {"message": "FastAPI boilerplate is running", "internal_ip": server_internal_ip}



@app.post("/register")
async def register(
    data: Registration,
    request: Request
):
    ip = request.client.host


    devices[data.device_id] = {
        "ip": ip
    }

    #based on current number of registered devices, assign a unique device id to the new device and store it in the devices dictionary
    # device_id = f"device_{len(devices) + 1}"
    devices[data.device_id] = {
        "ip": ip,
        "last_seen": datetime.now(timezone.utc)
    }

    print(f"Registered device {data.device_id} with IP {ip} at {datetime.now(timezone.utc)}")
    print(f"Current registered devices: {devices}")

    return {"status": "ok"}


#get request : return the intensity of both channels for a device
# temperature of the light sources in solar simulator to be received

# FRONTEND CALLS THIS ENDPOINT TO SET THE INTENSITY OF A CHANNEL ON A DEVICE
@app.get("/set/{device_id}/{channel}/{intensity}")
async def set(device_id: str, channel: str, intensity: int):

    # sample request :
    # http://127.0.0.1:8000/set/solar_simulator_01/ch0/50

    print(f"Setting channel {channel} to intensity {intensity}")

    # retrieve the device IP from the registered devices
    ip = devices[device_id]

    #debug print
    print("ip is ", ip)

    # make a request to the device to set the intensity : using get request
    # the request is made to the device's IP with the endpoint /set and query parameters ch0 or ch1 depending on the channel and intensity as the value
    # request parameters example : http://device_ip/set?ch0=50 or http://device_ip/set?ch1=50 or http://device_ip/set?ch0=50&ch1=50
    try:
        # below code is an io bound operation so can be made asynchronous using httpx library instead of requests library for better performance and scalability
        response = requests.get(

            f"http://{ip['ip']}/set",

            params={
                "ch0": intensity if channel == "ch0" else None,
                "ch1": intensity if channel == "ch1" else None,
            },

            timeout = 30
        )

        return {"status": "ok", "response": response.status_code}

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": str(e)
        }


# FRONTEND CALLS THIS ENDPOINT TO SET THE INTENSITY OF BOTH CHANNELS ON A DEVICE
# FRONTEND KNOWS THE DEVICE_ID BUT THE ROUTING TO CORRECT IP IS DONE BY THE BACKEND USING THE DEVICES DICTIONARY
@app.post("/set/{device_id}")
async def set_device(device_id: str, payload: SetRequest):

    # sample request :
    # http://127.0.0.1:8000/set/solar_simulator_01/ with JSON body {"ch0": 50, "ch1": 70}

    #how to test this endpoint using curl :
    # curl -Method POST "http://127.0.0.1:8000/set/solar_simulator_01/" `
    #  -ContentType "application/json" `
    #  -Body '{"ch0":25,"ch1":80}'

    if device_id not in devices:
        return {
            "status": "error",
            "message": f"Device {device_id} not registered"
        }
    
    ip = devices[device_id]   # FastAPI resolves ESP32 IP

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{ip['ip']}/set",
                params={
                    "ch0": payload.ch0,
                    "ch1": payload.ch1
            },
            timeout=15
        )

        return {
            "esp32_response": response.text
        }
    
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    

# HEARTBEAT
@app.post("/heartbeat")
async def heartbeat(data: Heartbeat):
    if(data.device_id not in devices):
        print(f"Received heartbeat from unregistered device {data.device_id} with IP {data.ip} at {datetime.now(timezone.utc)}")
    else:
        devices[data.device_id] = {
            "ip": data.ip,
            "last_seen": datetime.now(timezone.utc),
            "online": True
        }

    print(f"Received heartbeat from device {data.device_id} with IP {data.ip} at {datetime.now(timezone.utc)}")

    return {"status": "ok"}


# retrieve temperature of the light sources in solar simulator to be received
# ui will call this endpoint to get the temperature of the light sources in solar simulator and display it on the dashboard
# esp32 will receive get request from the backend and respond with the temperature of the light sources in solar simulator
# a get request will needed to be defined on the esp32 to receive the request from the backend and respond with the temperature of the light sources in solar simulator
@app.get("/temperature/{device_id}")
async def get_temperature(device_id: str):

    if device_id not in devices:
        return {
            "status": "error",
            "message": f"Device {device_id} not registered"
        }
    
    ip = devices[device_id]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{ip['ip']}/temperature",
                timeout=15
            )

            return {
                "temperature": response.text
            }
    
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    

#EMAIL ROUTE : SEND EMAIL REGARDING ANY ISSUE WITH THE SOLAR SIMULATOR : COULD BE TEMPERATURE / LIGHT INTENSITY
#RECEIVE A SPECIFIC CODE FROM ESP32 -> FASTAPI : WE CAN MAP THE ERROR CODES TO ISSUES
@app.post("/email/{device_id}")
async def send_email(data: ESPAlert):
    # 1. Instantiate the sender with our settings
    email_sender = EmailSender(config=email_settings)

    # 2. Read the HTML template from the file
    template_path = Path("templates/sample_email.html")
    html_template = template_path.read_text()

    alert_type = data.alert

    # 3. Define the content for the template
    template_body = {
        "alert_type" : alert_type
    }

    #later can add switch case : based on esp errors -> email needed
    #for eg : esperr1 : temperature error : esperr2 : light intensity error : esperr3 : something else

    # 4. Send the email : is this blocking
    success = await email_sender.send_email(
        email_to="sarveshvazarkar@gmail.com",
        subject="Alert from ESP",
        html_template=html_template,
        template_body=template_body,
    )

    if success:
        print("Email sent!")
    else:
        print("Failed to send email.")
