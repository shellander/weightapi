from weight3 import app
from flask import request, jsonify
from weight3 import db
from weight3.models import User, Measurement


from datetime import datetime

@app.route('/add_measurement', methods=['POST'])
def add_measurement():
    data = request.get_json()
    print(data)
    user_id = data.get('user_id')
    weight = data.get('weight')
    date_str = data.get('date')
    
    if not all([user_id, weight, date_str]):
        return jsonify({'error': 'Missing data'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    measurement = Measurement(user_id=user_id, weight=weight, date=date)
    db.session.add(measurement)
    db.session.commit()

    return jsonify({'success': 'Measurement added'}), 201

@app.route('/edit_measurement/<int:measurement_id>', methods=['PUT'])
def edit_measurement(measurement_id):
    data = request.get_json()

    user_id = data.get('user_id')
    weight = data.get('weight')
    date = data.get('date')

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    measurement = Measurement.query.get(measurement_id)
    if not measurement:
        return jsonify({'error': 'Measurement not found'}), 404

    if measurement.user_id != user_id:
        return jsonify({'error': 'Measurement does not belong to the specified user'}), 403

    if weight is not None:
        measurement.weight = weight
    if date is not None:
        measurement.date = date

    db.session.commit()

    return jsonify({'success': 'Measurement updated'}), 200

@app.route('/delete_measurement', methods=['DELETE'])
def delete_measurement():
    data = request.get_json()

    measurement_id = data.get('measurement_id')
    user_id = data.get('user_id')

    if not all([measurement_id, user_id]):
        return jsonify({'error': 'Missing measurement_id or user_id'}), 400

    measurement = Measurement.query.get(measurement_id)
    if not measurement:
        return jsonify({'error': 'Measurement not found'}), 404

    if measurement.user_id != user_id:
        return jsonify({'error': 'Measurement does not belong to the specified user'}), 403

    db.session.delete(measurement)
    db.session.commit()

    return jsonify({'success': 'Measurement deleted'}), 200


from flask import make_response

def measurement_to_dict(measurement):
    return {
        "id": measurement.id,
        "user_id": measurement.user_id,
        "weight": measurement.weight,
        "date": measurement.date.isoformat()
    }

@app.route('/get_measurements/<int:user_id>', methods=['GET'])
def get_measurements(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    measurements = Measurement.query.filter_by(user_id=user_id).order_by(Measurement.date).all()

    response = make_response(jsonify([measurement_to_dict(measurement) for measurement in measurements]))
    response.headers['Content-Type'] = 'application/json'

    return response

from datetime import datetime, timedelta

@app.route('/biggest_losers', methods=['GET'])
def biggest_losers():
    period = request.args.get('period', 'week').lower()

    if period not in ['week', 'month', 'all']:
        return jsonify({'error': 'Invalid period value. Accepted values are: week, month, all'}), 400

    if period == 'week':
        time_delta = timedelta(weeks=1)
    elif period == 'month':
        time_delta = timedelta(days=30)
    else:
        time_delta = None

    users = User.query.all()
    weight_losses = []

    for user in users:
        if time_delta:
            time_threshold = datetime.utcnow() - time_delta
            measurements = Measurement.query.filter(Measurement.user_id == user.id, Measurement.date >= time_threshold).order_by(Measurement.date).all()
        else:
            measurements = Measurement.query.filter_by(user_id=user.id).order_by(Measurement.date).all()

        if len(measurements) >= 2:
            weight_loss = measurements[0].weight - measurements[-1].weight
            weight_losses.append({'user_id': user.id, 'name': user.name, 'weight_loss': weight_loss})

    weight_losses.sort(key=lambda x: x['weight_loss'], reverse=True)
    response = make_response(jsonify(weight_losses))
    response.headers['Content-Type'] = 'application/json'

    return response

# @app.route('/biggest_losers', methods=['GET'])
# def biggest_losers():
#     one_week_ago = datetime.utcnow() - timedelta(weeks=1)

#     users = User.query.all()
#     weight_losses = []

#     for user in users:
#         last_week_measurements = Measurement.query.filter(Measurement.user_id == user.id, Measurement.date >= one_week_ago).order_by(Measurement.date).all()

#         if len(last_week_measurements) >= 2:
#             weight_loss = last_week_measurements[0].weight - last_week_measurements[-1].weight
#             weight_losses.append({'user_id': user.id, 'name': user.name, 'weight_loss': weight_loss})

#     weight_losses.sort(key=lambda x: x['weight_loss'], reverse=True)
#     response = make_response(jsonify(weight_losses))
#     response.headers['Content-Type'] = 'application/json'

#     return response

@app.route('/get_user_id', methods=['POST'])
def get_user_id():
    data = request.get_json()

    name = data.get('name')
    email = data.get('email')

    if not all([name, email]):
        return jsonify({'error': 'Missing data'}), 400

    user = User.query.filter_by(name=name, email=email).first()

    if not user:
        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()

    return jsonify({'user_id': user.id}), 200

@app.route('/get_user_measurements', methods=['GET'])
def get_user_measurements():
    user_id = request.args.get('user_id')
    period = request.args.get('period', 'week').lower()

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    if period not in ['week', 'month', 'all']:
        return jsonify({'error': 'Invalid period value. Accepted values are: week, month, all'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if period == 'week':
        time_delta = timedelta(weeks=1)
    elif period == 'month':
        time_delta = timedelta(days=30)
    else:
        time_delta = None

    if time_delta:
        time_threshold = datetime.utcnow().date() - time_delta
        measurements = Measurement.query.filter(Measurement.user_id == user.id, Measurement.date >= time_threshold).order_by(Measurement.date).all()
    else:
        measurements = Measurement.query.filter_by(user_id=user.id).order_by(Measurement.date).all()

    measurement_dicts = [{'id': m.id, 'weight': m.weight, 'date': m.date.isoformat()} for m in measurements]
    response = make_response(jsonify(measurement_dicts))
    response.headers['Content-Type'] = 'application/json'

    return response

@app.route('/get_all_userdata', methods=['GET'])
def get_all_userdata():
    period = request.args.get('period', 'week').lower()

    if period not in ['week', 'month', 'all']:
        return jsonify({'error': 'Invalid period value. Accepted values are: week, month, all'}), 400

    if period == 'week':
        time_delta = timedelta(weeks=1)
    elif period == 'month':
        time_delta = timedelta(days=30)
    else:
        time_delta = None

    users = User.query.all()
    userdata = []

    for user in users:
        if time_delta:
            time_threshold = datetime.utcnow().date() - time_delta
            measurements = Measurement.query.filter(Measurement.user_id == user.id, Measurement.date >= time_threshold).order_by(Measurement.date).all()
        else:
            measurements = Measurement.query.filter_by(user_id=user.id).order_by(Measurement.date).all()

        measurement_dicts = [{'id': m.id, 'weight': m.weight, 'date': m.date.isoformat()} for m in measurements]
        userdata.append({'user_id': user.id, 'name': user.name, 'measurements': measurement_dicts})

    response = make_response(jsonify(userdata))
    response.headers['Content-Type'] = 'application/json'

    return response


@app.route('/', methods=["GET"])
def home():
    return "OK"

if __name__ == '__main__':
    import os
    print("URL MAP")
    print(app.url_map)
    print(os.environ.get('DATABASE_URL'))
    app.run(debug=True, port=9999)