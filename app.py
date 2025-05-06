from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
from typing import Optional
from werkzeug.exceptions import HTTPException
from dateutil.parser import isoparse
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

mongo_host = os.getenv('MONGO_HOST', 'localhost')  # Fallback zu 'localhost' falls MONGO_HOST nicht gesetzt ist
mongo_port = int(os.getenv('MONGO_PORT', '27017'))  # Fallback zu '27017' falls MONGO_PORT nicht gesetzt ist

# Verbinde mit der MongoDB-Datenbank
client = MongoClient(host=mongo_host, port=mongo_port)
db = client['test']
collection_events = db['events']
collection_todolists = db['todolists']
collection_notes = db['notes']
collection_recipes = db['recipes']
collection_recommendations = db['recommendations']
collection_gameConfigs = db['gameConfigs']

# Pydantic-Modell für das Event
class Event(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    description: Optional[str] = ""
    participants: int
    location: Optional[str] = ""
    start: datetime
    end: datetime
    person: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Pydantic-Modell für das ToDo
class ToDo(BaseModel):
	context: str
	active: bool

# Pydantic-Modell für die ToDoList
class ToDoList(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    creator: str
    person: str
    title: str
    list: List[ToDo]
    created_at: datetime
    last_edited: datetime

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Pydantic-Modell für das Note
class Note(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    content: Optional[str] = ""
    created_at: str
    last_edited: str
    person: str
    creator: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Pydantic-Modell für das Ingredient
class Ingredient(BaseModel):
    name: str
    amount: int
    unit: str


# Pydantic-Modell für das Recipe
class Recipe(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    owner: str
    ingredients: List[Ingredient]
    guide: str
    persons: int

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Pydantic-Modell für das Recommendation
class Recommendation(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    creator: str
    description: str
    type: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class GameConfig(BaseModel): 
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    configName: str
    rufspielTarif: int
    soloTarif: int
    bonusTarif: int
    alleWeiter: str 
    soloArten: List[str]
    hochzeit: bool
    klopfen: bool
    ramschTarif: int

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


@app.route('/vevent/get', methods=['POST'])
def get_events():

    query_conditions = []

    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()

        # Lese Start- und Enddaten sowie Personen aus dem Payload
        start = isoparse(data['start'])
        end = isoparse(data['end'])
        persons = data['persons']
        is_salettl = data.get('isSalettl', False)

        query_conditions.append({ 'person': { '$in': persons } })
        query_conditions.append({ 'start': { '$lt': end } })
        query_conditions.append({ 'end': { '$gt': start } })

        if is_salettl:
            query_conditions.append({ 'location': 'Salettl' })

        # Ausfuehren
        results = collection_events.find({ '$and': query_conditions })

        # Konvertiere die Ergebnisse in eine Liste von Dictionaries
        results_list = list(results)

        # Konvertiere die _id-Felder von ObjectId in Strings, da JSON diese nicht direkt unterstuetzt
        for event in results_list:
            event['_id'] = str(event['_id'])

        # Gib die Ergebnisse als JSON zurueck
        return jsonify(results_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/vevent/new', methods=['POST'])
def create_event():
    try:
            data = request.get_json()

            # Überprüfe, ob 'id' fehlt oder ein leerer String ist, und generiere eine neue ObjectId
            if not data.get('_id') or data['_id'] == "":
                data['_id'] = str(ObjectId())

            event = Event(**data)
            event_dict = event.dict(by_alias=True)

            # Füge das Event in die MongoDB ein
            result = collection_events.insert_one(event_dict)

            # Rückgabe des eingefügten Events mit der generierten _id
            return jsonify({"success": True, "inserted_id": str(result.inserted_id)})

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/vevent/edit', methods=['POST'])
def edit_event():
    try:
        data = request.get_json()
        event_id = data['_id']

        update_data = {k: v for k, v in data.items() if k != '_id'}

        # Konvertiere die Zeitfelder in datetime-Objekte
        if 'start' in update_data:
            update_data['start'] = isoparse(update_data['start'])
        if 'end' in update_data:
            update_data['end'] = isoparse(update_data['end'])

        # Debugging-Ausgabe für die ID und die Update-Daten
        print("Event ID:", event_id)
        print("Update Data:", update_data)

        result = collection_events.update_one({"_id": event_id}, {"$set": update_data})
        print("Matched Count:", result.matched_count)

        if result.matched_count:
            return jsonify({"success": True, "updated_id": event_id})
        else:
            return jsonify({"error": "Event not found"}), 404

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/vevent/delete', methods=['POST'])
def delete_event():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()
        event_id = data['_id']

        # Bei Strings keine Konvertierung zu ObjectId vornehmen, falls sie als String gespeichert sind
        result = collection_events.delete_one({"_id": event_id})

        if result.deleted_count:
            return jsonify({"success": True, "deleted_id": event_id})
        else:
            return jsonify({"error": "Event not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vnote/get', methods=['POST'])
def get_notes():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()

        # Lese Payload
        person = data['person']

        # Füge eine exakte Übereinstimmung hinzu (kein $in, sondern direkte Abfrage)
        query_conditions = { 'person': person }

        # Führe die Abfrage aus
        results = collection_notes.find(query_conditions)

        # Konvertiere die Ergebnisse in eine Liste von Dictionaries
        results_list = list(results)

        # Konvertiere die _id-Felder von ObjectId in Strings, da JSON diese nicht direkt unterstützt
        for note in results_list:
            note['_id'] = str(note['_id'])

        # Gib die Ergebnisse als JSON zurück
        return jsonify(results_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/vnote/new', methods=['POST'])
def create_note():
    try:
            data = request.get_json()

            # Überprüfe, ob 'id' fehlt oder ein leerer String ist, und generiere eine neue ObjectId
            if not data.get('_id') or data['_id'] == "":
                data['_id'] = str(ObjectId())

            note = Note(**data)
            note_dict = note.dict(by_alias=True)

            # Füge das Event in die MongoDB ein
            result = collection_notes.insert_one(note_dict)

            # Rückgabe des eingefügten Events mit der generierten _id
            return jsonify({"success": True, "inserted_id": str(result.inserted_id)})

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/vnote/delete', methods=['POST'])
def delete_note():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()
        note_id = data['_id']

        # Bei Strings keine Konvertierung zu ObjectId vornehmen, falls sie als String gespeichert sind
        result = collection_notes.delete_one({"_id": note_id})

        if result.deleted_count:
            return jsonify({"success": True, "deleted_id": note_id})
        else:
            return jsonify({"error": "Note not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vtodolist/get', methods=['POST'])
def get_todolists():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()

        # Lese Payload
        person = data['person']

        # Füge eine exakte Übereinstimmung hinzu (kein $in, sondern direkte Abfrage)
        query_conditions = { 'person': person }

        # Führe die Abfrage aus
        results = collection_todolists.find(query_conditions)

        # Konvertiere die Ergebnisse in eine Liste von Dictionaries
        results_list = list(results)

        # Konvertiere die _id-Felder von ObjectId in Strings, da JSON diese nicht direkt unterstützt
        for todolist in results_list:
            todolist['_id'] = str(todolist['_id'])

        # Gib die Ergebnisse als JSON zurück
        return jsonify(results_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/vtodolist/new', methods=['POST'])
def create_todolist():
    try:
            data = request.get_json()

            # Überprüfe, ob 'id' fehlt oder ein leerer String ist, und generiere eine neue ObjectId
            if not data.get('_id') or data['_id'] == "":
                data['_id'] = str(ObjectId())

            todolist = ToDoList(**data)
            todolist_dict = todolist.dict(by_alias=True)

            # Füge das Event in die MongoDB ein
            result = collection_todolists.insert_one(todolist_dict)

            # Rückgabe des eingefügten Events mit der generierten _id
            return jsonify({"success": True, "inserted_id": str(result.inserted_id)})

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/vtodolist/edit', methods=['POST'])
def edit_todolist():
    try:
        data = request.get_json()
        todolist_id = data['_id']

        update_data = {k: v for k, v in data.items() if k != '_id'}

        # Konvertiere die Zeitfelder in datetime-Objekte
        if 'created_at' in update_data:
            update_data['created_at'] = isoparse(update_data['created_at'])
        if 'last_edited' in update_data:
            update_data['last_edited'] = isoparse(update_data['last_edited'])

        # Debugging-Ausgabe für die ID und die Update-Daten
        print("ToDoList ID:", todolist_id)
        print("Update Data:", update_data)

        result = collection_todolists.update_one({"_id": todolist_id}, {"$set": update_data})
        print("Matched Count:", result.matched_count)

        if result.matched_count:
            return jsonify({"success": True, "updated_id": str(todolist_id)})
        else:
            return jsonify({"error": "To-Do List not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vtodolist/delete', methods=['POST'])
def delete_todolist():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()
        todolist_id = data['_id']

        # Bei Strings keine Konvertierung zu ObjectId vornehmen, falls sie als String gespeichert sind
        result = collection_todolists.delete_one({"_id": todolist_id})

        if result.deleted_count:
            return jsonify({"success": True, "deleted_id": todolist_id})
        else:
            return jsonify({"error": "Note not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vrecipe/get', methods=['POST'])
def get_recipes():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json(silent=True)

        # Führe die Abfrage aus
        results = collection_recipes.find()

        # Konvertiere die Ergebnisse in eine Liste von Dictionaries
        results_list = list(results)

        # Konvertiere die _id-Felder von ObjectId in Strings, da JSON diese nicht direkt unterstützt
        for recipe in results_list:
            recipe['_id'] = str(recipe['_id'])

        # Gib die Ergebnisse als JSON zurück
        return jsonify(results_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/vrecipe/new', methods=['POST'])
def create_recipe():
    try:
            data = request.get_json()

            # Überprüfe, ob 'id' fehlt oder ein leerer String ist, und generiere eine neue ObjectId
            if not data.get('_id') or data['_id'] == "":
                data['_id'] = str(ObjectId())

            recipe = Recipe(**data)
            recipe_dict = recipe.dict(by_alias=True)

            # Füge das Event in die MongoDB ein
            result = collection_recipes.insert_one(recipe_dict)

            # Rückgabe des eingefügten Events mit der generierten _id
            return jsonify({"success": True, "inserted_id": str(result.inserted_id)})

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/vrecipe/edit', methods=['POST'])
def edit_recipe():
    try:
        data = request.get_json()
        recipe_id = data['_id']

        update_data = {k: v for k, v in data.items() if k != '_id'}

        result = collection_recipes.update_one({"_id": recipe_id}, {"$set": update_data})
        print("Matched Count:", result.matched_count)

        if result.matched_count:
            return jsonify({"success": True, "updated_id": str(recipe_id)})
        else:
            return jsonify({"error": "To-Do List not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vrecipe/delete', methods=['POST'])
def delete_recipe():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()
        recipe_id = data['_id']

        # Bei Strings keine Konvertierung zu ObjectId vornehmen, falls sie als String gespeichert sind
        result = collection_recipes.delete_one({"_id": recipe_id})

        if result.deleted_count:
            return jsonify({"success": True, "deleted_id": recipe_id})
        else:
            return jsonify({"error": "Note not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vrecommendation/get', methods=['POST'])
def get_recommendations():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()

        # Hole den Typ, wenn er vorhanden ist, andernfalls leere Zeichenfolge
        type = data.get('type', "")

        # Füge eine exakte Übereinstimmung hinzu (kein $in, sondern direkte Abfrage)
        if type != "":
            query_conditions = { 'type': type }
            # Führe die Abfrage aus
            results = collection_recommendations.find(query_conditions)
        else:
            # Wenn kein Typ angegeben ist, gib alle Ergebnisse zurück
            results = collection_recommendations.find()

        # Konvertiere die Ergebnisse in eine Liste von Dictionaries
        results_list = list(results)

        # Konvertiere die _id-Felder von ObjectId in Strings, da JSON diese nicht direkt unterstützt
        for recommendation in results_list:
            recommendation['_id'] = str(recommendation['_id'])

        # Gib die Ergebnisse als JSON zurück
        return jsonify(results_list)

    except Exception as e:
        # Gib einen Fehler zurück, falls etwas schiefgeht
        return jsonify({'error': str(e)}), 400

@app.route('/vrecommendation/new', methods=['POST'])
def create_recommendation():
    try:
        data = request.get_json()

        # Überprüfe, ob 'id' fehlt oder ein leerer String ist, und generiere eine neue ObjectId
        if not data.get('_id') or data['_id'] == "":
            data['_id'] = str(ObjectId())

        recommendation = Recommendation(**data)

        recommendation_dict = recommendation.dict(by_alias=True)

        # Füge das Event in die MongoDB ein
        result = collection_recommendations.insert_one(recommendation_dict)

        # Rückgabe des eingefügten Events mit der generierten _id
        return jsonify({"success": True, "inserted_id": str(result.inserted_id)})

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/vrecommendation/edit', methods=['POST'])
def edit_recommendation():
    try:
        data = request.get_json()
        recommendation_id = data['_id']

        update_data = {k: v for k, v in data.items() if k != '_id'}

        result = collection_recommendations.update_one({"_id": recommendation_id}, {"$set": update_data})
        print("Matched Count:", result.matched_count)

        if result.matched_count:
            return jsonify({"success": True, "updated_id": str(recommendation_id)})
        else:
            return jsonify({"error": "To-Do List not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vrecommendation/delete', methods=['POST'])
def delete_recommendation():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()
        recommendation_id = data['_id']

        # Bei Strings keine Konvertierung zu ObjectId vornehmen, falls sie als String gespeichert sind
        result = collection_recommendations.delete_one({"_id": recommendation_id})

        if result.deleted_count:
            return jsonify({"success": True, "deleted_id": recommendation_id})
        else:
            return jsonify({"error": "Note not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/vgameConfig/get', methods=['POST'])
def get_gameConfigs():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json(silent=True)

        # Führe die Abfrage aus
        results = collection_gameConfigs.find()

        # Konvertiere die Ergebnisse in eine Liste von Dictionaries
        results_list = list(results)

        # Konvertiere die _id-Felder von ObjectId in Strings, da JSON diese nicht direkt unterstützt
        for gameConfig in results_list:
            gameConfig['_id'] = str(gameConfig['_id'])

        # Gib die Ergebnisse als JSON zurück
        return jsonify(results_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/vgameConfig/new', methods=['POST'])
def create_gameConfig():
    try:
        data = request.get_json()

        # Überprüfe, ob 'id' fehlt oder ein leerer String ist, und generiere eine neue ObjectId
        if not data.get('_id') or data['_id'] == "":
            data['_id'] = str(ObjectId())

        gameConfig = GameConfig(**data)

        gameConfig_dict = gameConfig.dict(by_alias=True)

        # Füge das Event in die MongoDB ein
        result = collection_gameConfigs.insert_one(gameConfig_dict)

        # Rückgabe des eingefügten Events mit der generierten _id
        return jsonify({"success": True, "inserted_id": str(result.inserted_id)})

    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/vgameConfig/edit', methods=['POST'])
def edit_gameConfig():
    try:
        data = request.get_json()
        gameConfig_id = data['_id']

        update_data = {k: v for k, v in data.items() if k != '_id'}

        result = collection_gameConfigs.update_one({"_id": gameConfig_id}, {"$set": update_data})
        print("Matched Count:", result.matched_count)

        if result.matched_count:
            return jsonify({"success": True, "updated_id": str(gameConfig_id)})
        else:
            return jsonify({"error": "To-Do List not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vgameConfig/delete', methods=['POST'])
def delete_gameConfig():
    try:
        # Hole das JSON-Payload aus der Anfrage
        data = request.get_json()
        gameConfig_id = data['_id']

        # Bei Strings keine Konvertierung zu ObjectId vornehmen, falls sie als String gespeichert sind
        result = collection_gameConfigs.delete_one({"_id": gameConfig_id})

        if result.deleted_count:
            return jsonify({"success": True, "deleted_id": gameConfig_id})
        else:
            return jsonify({"error": "Note not found"}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500    

if __name__ == '__main__':
	 app.run(host='localhost', port=8000)
