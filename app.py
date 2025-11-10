# hi so here is my entire code logic : here i tried my best to write my final code optimal using OOD concepts i had learned so far as we as Exceptional handling for redundant functunality.
# thanks for giving me this oppurtunity :) .
import os
import uuid
from flask import Flask, render_template, jsonify, abort
from pymongo import MongoClient, ReturnDocument
from dotenv import load_dotenv
from pymongo.errors import CollectionInvalid, PyMongoError
from functools import wraps

# loading environment variables from .env file
load_dotenv()

# getting env vars
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DATABASE_NAME", "intern_task")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "live_sessions")
COUNTER_COLLECTION = "counters"

# quick check in case .env is not configured
if not MONGO_URI:
    raise RuntimeError("MONGODB_URI not set in .env")

# initializing flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# connecting to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# initializing collections
collection = db[COLLECTION_NAME]
counters = db[COUNTER_COLLECTION]


# ------------------ Helper Section ------------------

# basic decorator for handling errors cleanly
def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PyMongoError as e:
            print(f"[DB ERROR] {str(e)}")
            return jsonify({"error": "Database operation failed"}), 500
        except Exception as e:
            print(f"[SERVER ERROR] {str(e)}")
            return jsonify({"error": "Something went wrong on server"}), 500
    return wrapper


# Class based structure (OOP approach) for DB related actions
class SessionManager:
    """Handles all DB operations related to live_sessions"""

    def __init__(self, db, collection_name, counter_collection):
        self.db = db
        self.collection = db[collection_name]
        self.counters = db[counter_collection]
        self.collection_name = collection_name

    def ensure_counter(self):
        """makes sure a counter document exists for auto increment id"""
        self.counters.update_one(
            {"_id": self.collection_name},
            {"$setOnInsert": {"seq": 0}},
            upsert=True
        )

    def get_next_id(self):
        """increments the counter and returns next id"""
        doc = self.counters.find_one_and_update(
            {"_id": self.collection_name},
            {"$inc": {"seq": 1}},
            return_document=ReturnDocument.AFTER
        )
        return doc["seq"]

    def create_collection_with_validator(self):
        """creates collection only if not exists with basic schema validation"""
        if self.collection_name in self.db.list_collection_names():
            return
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["id", "type", "unique_id", "userurl"],
                "properties": {
                    "id": {"bsonType": "int"},
                    "type": {"bsonType": "string", "enum": ["admin", "student"]},
                    "unique_id": {"bsonType": "string"},
                    "userurl": {"bsonType": "string"}
                }
            }
        }
        try:
            self.db.create_collection(self.collection_name, validator=validator)
            print(f"✅ Created collection `{self.collection_name}` with validator.")
        except CollectionInvalid:
            print("⚠️ Collection already exists or validation not permitted.")


# creating a manager instance (OOP)
session_manager = SessionManager(db, COLLECTION_NAME, COUNTER_COLLECTION)

# run startup setup
session_manager.create_collection_with_validator()
session_manager.ensure_counter()


# ------------------ Flask Routes ------------------

@app.route("/")
def index():
    """Home route -> admin page"""
    return render_template("index.html")


@app.route("/start-session", methods=["POST"])
@handle_exceptions
def start_session():
    """API to create a new live session for admin"""
    unique_id = str(uuid.uuid4())
    userurl = f"{get_base_url()}/session/{unique_id}"

    # auto incremented id
    new_id = session_manager.get_next_id()

    # preparing document for DB
    session_doc = {
        "id": new_id,
        "type": "admin",
        "unique_id": unique_id,
        "userurl": userurl
    }

    # inserting into DB
    result = collection.insert_one(session_doc)
    if not result.inserted_id:
        abort(500, "Failed to create session")

    # returning data as JSON
    return jsonify({
        "id": new_id,
        "type": "admin",
        "unique_id": unique_id,
        "userurl": userurl
    })


@app.route("/session/<unique_id>")
@handle_exceptions
def join_session(unique_id):
    """Student view (accessing the session via shared URL)"""
    session = collection.find_one({"unique_id": unique_id})
    if not session:
        # if no session found, render not found message
        return render_template("session.html", error="Session not found", unique_id=unique_id), 404
    # if session exists, render the same video screen
    return render_template("session.html", unique_id=unique_id, userurl=session.get("userurl"))


# helper function to build base URL dynamically
def get_base_url():
    # for local run
    return "https://internshiptask-session.vercel.app"


# main app runner
if __name__ == "__main__":
    app.run(debug=True)
