#!/usr/bin/env python3
import os
from flask import Flask, request, make_response, jsonify
from flask_migrate import Migrate
from flask_restful import Api, Resource
from models import db, Restaurant, RestaurantPizza, Pizza

# Set base directory and database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")

# Initialize Flask app
app = Flask(__name__)

# Configure Flask app
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
api = Api(app)

# Routes
@app.route("/")
def index():
    return "<h1>Welcome to the Pizza Restaurant API!</h1>"

# RESTful resources

class RestaurantListResource(Resource):
    def get(self):
        restaurants = Restaurant.query.all()
        return [restaurant.to_dict(only=("id", "name", "address")) for restaurant in restaurants], 200

class RestaurantResource(Resource):
    def get(self, id):
        restaurant = Restaurant.query.get(id)
        if not restaurant:
            return {"error": "Restaurant not found"}, 404

        # Merge restaurant data with restaurant_pizzas and associated pizza info
        restaurant_data = restaurant.to_dict(only=("id", "name", "address"))
        restaurant_data["restaurant_pizzas"] = [
            rp.to_dict(only=("id", "pizza_id", "restaurant_id", "price")) | {
                "pizza": rp.pizza.to_dict(only=("id", "name", "ingredients"))
            }
            for rp in restaurant.restaurant_pizzas
        ]
        return restaurant_data, 200

    def delete(self, id):
        restaurant = Restaurant.query.get(id)
        if not restaurant:
            return {"error": "Restaurant not found"}, 404

        # Delete associated RestaurantPizzas before deleting the restaurant
        for rp in restaurant.restaurant_pizzas:
            db.session.delete(rp)
        
        db.session.delete(restaurant)
        db.session.commit()
        return '', 204  # No content, successful deletion

class PizzaListResource(Resource):
    def get(self):
        pizzas = Pizza.query.all()
        return [pizza.to_dict(only=("id", "name", "ingredients")) for pizza in pizzas], 200

class RestaurantPizzaResource(Resource):
    def post(self):
        data = request.get_json()
        price = data.get("price")
        pizza_id = data.get("pizza_id")
        restaurant_id = data.get("restaurant_id")

        # Ensure all required fields are provided
        if not price or not pizza_id or not restaurant_id:
            return {"errors": ["Missing required fields: price, pizza_id, restaurant_id"]}, 400

        # Ensure valid pizza and restaurant exist
        pizza = Pizza.query.get(pizza_id)
        restaurant = Restaurant.query.get(restaurant_id)

        if not pizza or not restaurant:
            return {"errors": ["Invalid pizza_id or restaurant_id"]}, 400

        # Validate price
        if price < 1 or price > 30:
            return {"errors": ["Price must be between 1 and 30"]}, 400

        # Create and add the new RestaurantPizza
        restaurant_pizza = RestaurantPizza(price=price, pizza_id=pizza_id, restaurant_id=restaurant_id)
        db.session.add(restaurant_pizza)
        db.session.commit()

        # Return the created RestaurantPizza with serialized data
        restaurant_pizza_data = restaurant_pizza.to_dict(
            only=("id", "price", "pizza_id", "restaurant_id")
        )
        restaurant_pizza_data["pizza"] = pizza.to_dict(only=("id", "name", "ingredients"))
        restaurant_pizza_data["restaurant"] = restaurant.to_dict(only=("id", "name", "address"))
        
        return jsonify(restaurant_pizza_data), 201

# Add resources to API
api.add_resource(RestaurantListResource, "/restaurants")
api.add_resource(RestaurantResource, "/restaurants/<int:id>")
api.add_resource(PizzaListResource, "/pizzas")
api.add_resource(RestaurantPizzaResource, "/restaurant_pizzas")

# Error handling
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Run the app
if __name__ == "__main__":
    app.run(port=5555, debug=True)
