"""
Source Name: SSTimeUtilities.py
Version: ArcGIS 10.1
Author: ESRI

A series of functions that help work with time in ArcGIS.
"""

################### Imports ########################
import sys as SYS
import os as OS
import locale as LOCALE
import numpy as NUM
import random as PYRAND
import arcpy as ARCPY
import ErrorUtils as ERROR
import SSUtilities as UTILS
import datetime as DT
import calendar as CAL

########################## Constants #############################
lastDays = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 
            7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

######################### General Functions ###########################

def calculateTimeWindow(timeStamp, timeValue, timeType):

    #### Set Time Type/Value ####
    if timeType == "SECONDS":
        time0 = unitAdd(timeStamp, seconds = -timeValue)
        time1 = unitAdd(timeStamp, seconds = timeValue)
    elif timeType == "MINUTES":
        time0 = unitAdd(timeStamp, minutes = -timeValue)
        time1 = unitAdd(timeStamp, minutes = timeValue)
    elif timeType == "HOURS":
        time0 = unitAdd(timeStamp, hours = -timeValue)
        time1 = unitAdd(timeStamp, hours = timeValue)
    elif timeType == "DAYS":
        time0 = unitAdd(timeStamp, days = -timeValue)
        time1 = unitAdd(timeStamp, days = timeValue)
    elif timeType == "WEEKS":
        time0 = unitAdd(timeStamp, weeks = -timeValue)
        time1 = unitAdd(timeStamp, weeks = timeValue)
    elif timeType == "MONTHS":
        time0 = unitAdd(timeStamp, months = -timeValue)
        time1 = unitAdd(timeStamp, months = timeValue)
    else:
        time0 = unitAdd(timeStamp, years = -timeValue)
        time1 = unitAdd(timeStamp, years = timeValue)

    return time0, time1

def isTimeNeighbor(startDT, endDT, candidateDT):
    if candidateDT >= startDT and candidateDT <= endDT:
        return True
    else:
        return False

def unitAdd(inDateTime, seconds = 0, minutes = 0, hours = 0, 
            days = 0, weeks = 0, months = 0, years = 0):

    #### Weeks Through Seconds ####
    timeDelta = DT.timedelta(seconds = seconds, minutes = minutes, 
                             hours = hours, days = days, weeks = weeks)
    inDateTime = inDateTime + timeDelta

    #### Calculate Months ####
    if months:
        cmonth = inDateTime.month + months
        year = inDateTime.year
        if cmonth > 12:
            years += cmonth/12
            cmonth %= 12
            if cmonth == 0:
                years -= 1
                cmonth = 12
        elif cmonth < 1:
            years += (cmonth - 1) / 12
            cmonth = cmonth % 12
            if cmonth == 0:
                cmonth = 12

        end_date = monthConvert(cmonth, year)
        if inDateTime.day > end_date:
            inDateTime = inDateTime.replace(day = end_date, month = cmonth, year = year)
        else:
            inDateTime = inDateTime.replace(month = cmonth, year = year)

    #### Calculate Years ####
    if years:
        month = inDateTime.month
        year = inDateTime.year
        end_date = monthConvert(month, year+years)
        if inDateTime.day > end_date:
            inDateTime = inDateTime.replace(day = end_date, 
                            year = inDateTime.year + years)
        else:
            inDateTime = inDateTime.replace(year = inDateTime.year + years)

    return inDateTime

def monthConvert(month, year):
    if month == 2 and CAL.isleap(year):
        return 29
    else:
        return lastDays[month]

def iso2DateTime(dtString):
    return DT.datetime.strptime(dtString, "%Y-%m-%d %H:%M:%S")

