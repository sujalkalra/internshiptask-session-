import os
import uuid
from flask import Flask, render_template, jsonify, abort
from pymongo import MongoClient, ReturnDocument
from dotenv import load_dotenv
from pymongo.errors import CollectionInvalid

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DATABASE_NAME", "intern_task")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "live_sessions")
COUNTER_COLLECTION = "counters"

if not MONGO_URI:
    raise RuntimeError("MONGODB_URI not set in .env")

app = Flask(__name__, static_folder="static", template_folder="templates")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
counters = db[COUNTER_COLLECTION]


# Ensure a counter document exists for auto-increment id
def ensure_counter():
    counters.update_one(
        {"_id": COLLECTION_NAME},
        {"$setOnInsert": {"seq": 0}},
        upsert=True
    )


# Get next auto-increment id
def get_next_id():
    doc = counters.find_one_and_update(
        {"_id": COLLECTION_NAME},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER
    )
    return doc["seq"]


# Optionally create collection with basic JSON schema validation (if not exists)
def create_collection_with_validator():
    # only attempt if collection does not exist
    if COLLECTION_NAME in db.list_collection_names():
        return
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id", "type", "unique_id", "userurl"],
            "properties": {
                "id": {"bsonType": "int"},
                "type": {
                    "bsonType": "string",
                    "enum": ["admin", "student"]
                },
                "unique_id": {"bsonType": "string"},
                "userurl": {"bsonType": "string"}
            }
        }
    }
    try:
        db.create_collection(COLLECTION_NAME, validator=validator)
        print(f"Created collection `{COLLECTION_NAME}` with validator.")
    except CollectionInvalid:
        # collection already exists or not allowed by user permissions
        print("Could not create collection with validator (it may already exist or insufficient privileges).")


# Startup tasks
create_collection_with_validator()
ensure_counter()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start-session", methods=["POST"])
def start_session():
    unique_id = str(uuid.uuid4())
    userurl = f"{get_base_url()}/session/{unique_id}"
    new_id = get_next_id()

    session_doc = {
        "id": new_id,
        "type": "admin",
        "unique_id": unique_id,
        "userurl": userurl
    }

    result = collection.insert_one(session_doc)
    if not result.inserted_id:
        abort(500, "Failed to create session")

    # return the created session
    return jsonify({
        "id": new_id,
        "type": "admin",
        "unique_id": unique_id,
        "userurl": userurl
    })


@app.route("/session/<unique_id>")
def join_session(unique_id):
    session = collection.find_one({"unique_id": unique_id})
    if not session:
        return render_template("session.html", error="Session not found", unique_id=unique_id), 404
    return render_template("session.html", unique_id=unique_id, userurl=session.get("userurl"))


def get_base_url():
    # Running locally by default
    # If deployed, change this to your deployed domain (or build dynamically)
    return "http://localhost:5000"


if __name__ == "__main__":
    app.run(debug=True)
