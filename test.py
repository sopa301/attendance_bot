from util.db import *


def create_attendance(self, attendance_data):
  result = self.collection.insert_one(attendance_data)
  return result.inserted_id

def read_attendance(self, attendance_id):
  attendance = self.collection.find_one({'_id': attendance_id})
  return attendance

def delete_attendance(self, attendance_id):
  result = self.collection.delete_one({'_id': attendance_id})
  return result.deleted_count

# Example usage:
# from pymongo import MongoClient
# client = MongoClient('mongodb://localhost:27017/')
# db = client['your_database']
# attendance_list = AttendanceList(db)
# attendance_id = attendance_list.create_attendance({'name': 'John Doe', 'date': '2023-10-01'})
# print(attendance_list.read_attendance(attendance_id))
# print(attendance_list.delete_attendance(attendance_id))