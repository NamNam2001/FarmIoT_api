from fastapi import FastAPI, WebSocket, Request, Query,Response
from influxdb_client_3 import InfluxDBClient3, Point
import pandas
import numpy as np
# from influxdb_client_3 import flight_client_options
import certifi
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import matplotlib.pyplot as plt
import random
import asyncio
from pymongo import MongoClient
from bson.json_util import dumps
from datetime import datetime, timezone, timedelta
import influxdb_client, os, time
# from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import json
import uvicorn
import string

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from pymongo import ReturnDocument


# token = "3AHLeH9p7pbWiMTTykyPZpAXKSqJuYELavzt9qMR7KaKys1BqHcaP4JgGAOUWG8fVRLO8JYP6BrLHHX3ziqhbg=="
# org = "HTR"
# url = "http://localhost:8086"

# client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
# bucket="Farm_Iot"

# write_api = client.write_api(write_options=SYNCHRONOUS)
# query_api = client.query_api()

#MongoDB
uri_mongo = "mongodb+srv://namnam201:ve6frX8YqrHYzXzh@cluster0nam.jn87y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0Nam"
# Set the Stable API version when creating a new client

# Send a ping to confirm a successful connection

# # $env:INFLUXDB_TOKEN = "LHAC3K5CPhccJv4T63Glx7mxZi8jrptjWjpodbiFkPmbRza8QcSYeKai5MfaFm2vetBY-NDe_s0pNMd6yQVHwg=="
token_influx="nWCG-pCK_XNYy_5CcP7pq-qmWLhWexDia-Dyma1PIZNKreeL0Mq6V7z26CtbEOwO-rVe9W3ZsqT-Iv_-9rUwCg=="
host_influx="https://us-east-1-1.aws.cloud2.influxdata.com"
org_influx="Dev"
database_influx="huetronics"

client = InfluxDBClient3(host=host_influx, token=token_influx, org=org_influx, database = database_influx)

# # connect MongoDB
# client = MongoClient("mongodb://localhost:27017/")
# db = client["sensors_db"]
# collection = db['test']

# data_to_insert = {
#     "device_id": "esp32_001",
#     "status": "on",
#     'time': datetime.now(),
# }

# # Thêm dữ liệu vào cơ sở dữ liệu
# result = collection.insert_one(data_to_insert)

# InfluxDB connect local 


#initialize the server
app = FastAPI()
currentValue = {}
origins = ["*"]

app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            expose_headers=["Content-Range", "Range"],
            allow_headers=["Authorization", "Range", "Content-Range"],
        )

def formatted_device(result):
    formatted_device = {'id': str(result['_id']), 'name': result['name']}
    return formatted_device

def formatted_dashboard(result):
    formatted_dashboard = {'id': str(result['_id']), 'name': result['name'], 'devices': [str(device_id) for device_id in result['devices']]}
    return formatted_dashboard
# # gRPC read root certificates (only Windown)
# fh = open(certifi.where(), "r")
# cert = fh.read()
# fh.close()
# client = InfluxDBClient3.InfluxDBClient3(host=host, token=token, org=org, database = database , flight_client_options=flight_client_options(
#         tls_root_certs=cert))

#start the MongoDB server
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(uri_mongo, server_api=ServerApi('1'))
    app.mongodb = app.mongodb_client.iot_farm
    print("MongoDB Connected")


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close() 
    print("MongoDB Disconnected")

@app.get('/devices')
async def get_list_devices(response: Response)   :                                                                                                                                                                                                                 
    devices = await app.mongodb.devices.find().to_list(length=100)
    formatted_documents = [
        {'id': str(device['_id']), 'name': device['name']}
        for device in devices
    ]                                                   
    response.headers["Content-Range"] = f"items {1}-{5}/{20}"
    return formatted_documents

@app.post('/devices')
async def add_device(request: Request):
    payload = await request.json()  # await here
    # print(payload)
    add_device = await app.mongodb.devices.insert_one(payload)

    new_device = await app.mongodb.devices.find_one({"_id": add_device.inserted_id})
    
    return formatted_device(new_device)

@app.get('/devices/{device_id}')
async def get_device(device_id: str):
    # print(device_id)                                                                                                                                                                                                              
    device = await app.mongodb.devices.find_one({"_id": ObjectId(device_id)})
    # formatted_device = {'id': str(device['_id']), 'name': device['name']}                               
    # print(formatted_device)                 
    # response.headers["Content-Range"] = f"items {1}-{10-1}/{20}"
    return formatted_device(device)

@app.put('/devices/{device_id}')
async def update_device(device_id: str, request: Request):
    # Ensure the device_id from the path matches the id in the payload
    payload = await request.json()  # await here
    print(payload)
    
    # Update the device in the database
    update_device = await app.mongodb.devices.find_one_and_update(
        {"_id": ObjectId(device_id)},
        {"$set": {"name": payload["name"]}} ,
        return_document=ReturnDocument.AFTER
    )         
    # print(update_device) # update_device
    # else:
    return formatted_device(update_device)

@app.delete('/devices/{device_id}')
async def delete_device(device_id: str):
    delete_device = await app.mongodb.devices.delete_one({"_id": ObjectId(device_id)})
    if delete_device.deleted_count == 1:
        return {}
    else:
        return {"message": "Device not found"}


@app.get('/dashboards')
async def get_list_dashboards():
    dashboards = await app.mongodb.dashboards.find().to_list(length=100)
    formatted_dashboards = []
    for dashboard in dashboards:
        dashboard_id = str(dashboard['_id'])

        device_ids = [ObjectId(device_id) for device_id in dashboard.get('devices', [])]
        devices = await app.mongodb.devices.find({"_id": {"$in": device_ids}}).to_list(length=100)
        
        # Chuyển đổi kết quả truy vấn thành danh sách các tên device
        device_names = [device['name'] for device in devices]

        # Định dạng dashboard
        formatted_dashboard = {
            'id': dashboard_id,
            'name': dashboard.get('name'),
            'devices': device_names # Chuyển danh sách device_names thành chuỗi
        }

        print(device_ids)
        formatted_dashboards.append(formatted_dashboard)

    return formatted_dashboards

@app.post('/dashboards')
async def add_dashboard(request: Request):
    payload = await request.json() 
    payload["devices"] = [ObjectId(device_id) for device_id in payload["devices"]]
    # print(payload)

    add_dashboard = await app.mongodb.dashboards.insert_one(payload)

    new_dashboard = await app.mongodb.dashboards.find_one({"_id": add_dashboard.inserted_id})
    # formatted_dashboard = {'id': str(new_dashboard['_id']), 'name': new_dashboard['name'], 'devices': [str(device_id) for device_id in new_dashboard.get('devices', [])]}
    # devices = await app.mongodb.devices.find({"_id": {"$in": new_dashboard['devices']}}).to_list(length=100)
    # new_dashboard['devices'] = [device['name'] for device in devices]

    return formatted_dashboard(new_dashboard)

@app.get('/dashboards/{dashboard_id}')
async def get_dashboard(dashboard_id: str):
    dashboard = await app.mongodb.dashboards.find_one({"_id": ObjectId(dashboard_id)})
    # formatted_dashboard = {'id': str(dashboard['_id']), 'name': dashboard['name'], 'devices': [str(device_id) for device_id in dashboard.get('devices', [])]}

    return formatted_dashboard(dashboard)


@app.put('/dashboards/{dashboard_id}')
async def update_dashboard(dashboard_id: str, request: Request):
    payload = await request.json()
    # payload["devices"] = [ObjectId(device_id) for device_id in payload["devices"]]    print(payload)
    payload["devices"] = [ObjectId(device_id) for device_id in payload["devices"]]
    # print(payload)
    update_dashboard = await app.mongodb.dashboards.find_one_and_update(
        {"_id": ObjectId(dashboard_id)},
        {"$set": payload},
        return_document=ReturnDocument.AFTER
    )
    # formatted_dashboard = {'id': str(update_dashboard['_id']), 'name': update_dashboard['name'], 'devices': [str(device_id) for device_id in update_dashboard.get('devices', [])]}
    
    return formatted_dashboard(update_dashboard)

@app.delete('/dashboards/{dashboard_id}')
async def delete_dashboard(dashboard_id: str):
    delete_dashboard = await app.mongodb.dashboards.delete_one({"_id": ObjectId(dashboard_id)})
    if delete_dashboard.deleted_count == 1:
        return {}
    else:
        return {"message": "Dashboard not found"}

@app.get('/')
async def home():
    return "Farm_iot"

# @app.get('/dashboards')
# async def get_data():
#     values_query = []
#     query = """
#     from(bucket: "Farm_Iot")
#         |> range(start: -7d)
#         |> filter(fn: (r) => r["_measurement"] == "dashboard_data")
#         |> keep(columns: ["dashboard_id"])
#         |> distinct(column: "dashboard_id")
#         |> sort(columns: ["dashboard_id"])
#     """
#     tables = query_api.query(query, org="HTR")

#     for table in tables:
#         for record in table.records:
#             # time_record = (record["_time"]+ timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
#             value_query = {
#                 # "deviceId": record["device_id"],
#                 # "day": time_record.split()[0],
#                 # "time": time_record.split()[1],
#                 # "value": record["_value"]
#                 "dashboardId": record["dashboard_id"],
#             }
#             values_query.append(value_query)
#     return values_query

from typing import List

from pydantic import BaseModel
from fastapi import Path

def processEndDate(endData):
    year, month, day = map(int, endData.split('-'))
    try:
        endData = datetime(year=year, month=month, day=day)
    except ValueError:
            # Process endDate 
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            endData = datetime(
                year=next_year, month=next_month, day=1)
    return(endData.strftime('%Y-%m-%d'))
    

@app.get('/dashboards/{deviceId}/listTypes')
async def get_device_types(deviceId: str):
    query= f"""SELECT DISTINCT type
    FROM "{database_influx}"
    WHERE
    "value" IS NOT NULL
    AND
    "device_id" = '{deviceId}'"""

    tables = client.query(query=query, language='sql')
    df = tables.to_pandas().sort_values(by="type")
    types = df['type'].tolist()
    result = {
        "deviceId": deviceId,
        "types": types
    }
    print(result)
    return result

@app.get('/data/{dashboardId}/{deviceTypeId}')
async def get_dashboard_data(
    dashboardId: str,
    deviceTypeId: str,
    startDate: str ,
    endDate: str ):

    deviceId= deviceTypeId.split('-')[0]
    type= deviceTypeId.split('-')[1]

    endDate= processEndDate(endDate)
    print(endDate)
    # Do something with dashboardId, id, startDate, endDate
    device_query = {
        "device_id": deviceTypeId,
        "name": deviceTypeId,
        "data": [],
        "date": [""]
    }

    query = f"""SELECT *
    FROM "{database_influx}"
    WHERE
    time >= timestamp '{startDate}' AND time <= timestamp '{endDate}'
    AND
    ("value" IS NOT NULL)
    AND
    "device_id" IN ('{deviceId}') AND "type" IN ('{type}')"""

    # Execute the query
    tables = client.query(query=query, language='sql')
    print(tables)

    df = tables.to_pandas().sort_values(by="time")
   
    for index, record in df.iterrows():
            time_record = (record["time"] + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
            value = record["value"]
            
            device_query["data"].append(value)
            device_query["date"].append(time_record)
    print(device_query)
    return device_query
            
    #         # If device_id does not exist, create new entry
    #         if not device_exists:
    #             new_device_query = {  
    #                 "device_id": device_id,
    #                 "name": device_id,
    #                 "data": [value],
    #                 "date": ["", time_record]
    #             }
    #             dashboards_query["data"].append(new_device_query)
    
    # return dashboards_query



@app.post('/post-data/{dashboardId}/{id}')
async def add_sensor(dashboardId: str, id: str, request: Request):
    _json = await request.json()
    global currentValue 
    data = _json["value"]
    print("Data received")
    print(_json)
    
    #wiring data to influx
    points = []
    for valueType in data:
        point = (
            Point("huetronics") 
            .tag("device_id", str(id))
            .tag("type", str(valueType))  
            .field("value", float(data[valueType]))
        )
        points.append(point)

    print([point.to_line_protocol() for point in points])
    client.write(database=database_influx, record=points)
    points.clear()

    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    #wiring data to current Value
    if dashboardId not in currentValue:
        currentValue[dashboardId] = {}

    if id not in currentValue[dashboardId]:
        currentValue[dashboardId][id] = [data, random_string]
    else:
        currentValue[dashboardId][id] = [data, random_string]

    print(currentValue)

    # print("Data sent successfully")
   
#     # return {"message": "Data received successfully"}


@app.websocket("/socket/{dashboardId}/{deviceTypeId}")
async def websocket_endpoint(dashboardId: str, deviceTypeId: str, websocket: WebSocket):
    print('a new websocket to create.')
    await websocket.accept()
    # current_value = None
    random_string = ""
    last_update_time = None
    id = deviceTypeId.split('-')[0]
    type = deviceTypeId.split('-')[1]
    while True:
        try:
            if dashboardId in currentValue and id in currentValue[dashboardId]:
                if random_string != currentValue[dashboardId][id][1]:
                    random_string = currentValue[dashboardId][id][1]
                    last_update_time = datetime.now()
                    await websocket.send_json(currentValue[dashboardId][id][0][type])
                else:
                    if datetime.now() - last_update_time > timedelta(minutes=1):
                        del currentValue[dashboardId][id]
            else:
                await websocket.send_json(None)
            
            # print(currentValue[dashboardId][id][0][type])
            # else:
            #     continue
        except Exception as e:
            print('error:', e)
            break
        await asyncio.sleep(1) 
    print('Bye..')

if __name__ == "__main__":
    uvicorn.run("test:app", host="0.0.0.0", port=8000, log_level="info",reload=True)
