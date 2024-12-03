import os
from uuid import uuid4
from datetime import datetime, UTC
from pymongo import MongoClient

client = MongoClient(host=os.environ.get("DB_URI"))
db_name: str = os.environ.get("DB_NAME")
opd_dept_collection: str = os.environ.get("OPD_DEPT_COLLECTION")
pmgmt_collection: str = os.environ.get("PMGMT_COLLECTION")
doctors_collection: str = os.environ.get("DOCTORS_COLLECTION")

# Create new admission into emergency ward
def create_new_opd_appointment(patient_id: str):
  """Create new admission into emergency ward"""
  try:
    # check patient info from the patient mgmt database
    # if record exists, then proceed
    # otherwise notify the reason in the response

    lookup_result = lookup_patient(patient_id, db_name, pmgmt_collection)
    # print(lookup_result)
    if lookup_result is None:
      return {"error": True, "reason": f"No patient found with patient id {patient_id}"}
    
    medical_data = lookup_result["medical_info"]
    patient_basic_data = lookup_result["basic_info"]
    assigned_doctor: map = check_available_doctor(medical_data["department"])

    # create the appointment id
    appointment_id: str = str(uuid4())

    # create emergency admission
    # prepare the payload
    payload = {
      "appointment_id": appointment_id,
      "appointment_on": datetime.now(UTC),
      "patient_id": patient_id,
      "assigned_doctor": {
        "doctor_id": assigned_doctor["doctor_id"],
        "doctor_name": assigned_doctor["doctor_name"]
      },
      "patient_name": patient_basic_data["name"],
      "department": medical_data["department"],
      "history": medical_data["history"],
      "illness_primary": medical_data["illness_primary"]
    }

    insert_ok = client[db_name][opd_dept_collection].insert_one(payload).acknowledged
    if not insert_ok:
      return {"error": True, "reason": "db insertion failure"}
    return {"error": False, "status": "ok", "data": {"appointment_id": appointment_id}}
  except Exception as err:
    raise err
  

# Lookup patient info
def lookup_patient(patient_id: str, db_name: str, patient_mgmt_collection_name: str):
  """Lookup patient info"""
  try:
    patient_mgmt_collection = client[db_name][patient_mgmt_collection_name]
    result = patient_mgmt_collection.find_one({"medical_info.patientId": patient_id}, {"_id": 0})
    return result
  except Exception as err:
    raise err

# Get current date for today in the format YYYY-MM-DD
def get_today(datetime: datetime) -> str:
  """Get current date for today in the format YYYY-MM-DD"""
  return f"{datetime.year}-{datetime.month}-{datetime.day}"


# Assign available doctors from the doctors pool
def check_available_doctor(ward: str) -> dict[str, any]:
  """Check available doctors from the doctors pool"""
  try:
    doctors_cursor = client[db_name][doctors_collection].find({}, {"_id": 0})
    available_doctors_list_map = [doctor for doctor in doctors_cursor]
    return [doctor for doctor in available_doctors_list_map if doctor["department"] == ward and get_today(datetime.now()) not in doctor["unavailable_dates"]][0]
  except Exception as err:
    raise err