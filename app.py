from flask import Flask, request, jsonify
from vercel_kv_sdk import KV
import pandas as pd
from io import StringIO
import json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024  # 16 MB, adjust as needed

# Initialize Redis connection
redis_client = KV()

@app.route('/api/<key>', methods=['GET'])
def get_data(key):
    data = redis_client.get(key)
    if data:
        return jsonify(json.loads(data))
    else:
        return 'No data found for key: {}'.format(key), 404

@app.route('/api/<key>', methods=['POST'])
def store_data(key):
    if request.is_json:
        data = request.json
    else:
        data = request.data
    if not data or not isinstance(data, dict):
        return 'Invalid JSON data', 400
    redis_client.set(key, json.dumps(data))
    return jsonify({'message': 'Data stored for key: {}'.format(key), 'data': data})

@app.route('/api', methods=['GET'])
def list_data():
    return jsonify({'message': 'Welcome to the API'})

@app.route('/process/test', methods=['POST'])
def process_test():
    # Return processed data in a dictionary
    orgs_csv = request.form['orgs_csv']
    orgs_df = pd.read_csv(StringIO(orgs_csv), delimiter=",")
    return jsonify({"Hello":orgs_df.shape[0]})

@app.route('/process/dashboard', methods=['POST'])
def process_dashboard():
    events_csv = request.form['events_csv']
    orgs_csv = request.form['orgs_csv']

    # Ensure data is received correctly
    if not events_csv or not orgs_csv:
        return jsonify({"error": "Missing data"}), 400

    # Load and process the CSV data
    events_df = pd.read_csv(StringIO(events_csv), delimiter=";")
    orgs_df = pd.read_csv(StringIO(orgs_csv), delimiter=",")
    orgs_df['expiration'] = orgs_df['expiration'].replace('Expired', pd.NaT)
    orgs_df['expiration'] = pd.to_datetime(orgs_df['expiration'], errors='coerce')

    # Create maps
    org_map = pd.Series(orgs_df.organization_name.values, index=orgs_df.organization_uuid).to_dict()
    expiration_map = pd.Series(orgs_df.expiration.values, index=orgs_df.organization_uuid).to_dict()

    # Exclude specific users
    exclude_user_ids = [
        'dcc27352-6b00-4cc9-a489-462ab3a12bf3',
        '73fafd55-9745-4e85-b0c8-6214dd8c3bb1',
        '0bdaef3f-dbdc-4d20-b89f-be45ec426831',
        '1871d515-a053-11e8-b24e-000c29a82b4a',
        '19185a41-4497-46c1-9949-e8d1cadc2293'
    ]
    events_df = events_df[~events_df['user_id'].isin(exclude_user_ids)]

    # Convert timestamp to datetime
    events_df['created'] = pd.to_datetime(events_df['created'])
    events_df['week'] = events_df['created'].dt.isocalendar().week

    # KPI calculations
    new_users = events_df[(events_df['category'] == 'user') & (events_df['name'] == 'create')]
    new_users_per_week = new_users.groupby('week')['user_id'].nunique()
    new_users_detail = new_users[['week', 'user_id', 'value']].rename(columns={'value': 'organization_id'})

    for idx, row in new_users_detail.iterrows():
        user_id = row['user_id']
        user_events = events_df[(events_df['user_id'] == user_id) & (events_df['category'] == 'workspace') & (events_df['name'] == 'enter') & (events_df['user_id'] != events_df['value'])]
        if not user_events.empty:
            new_users_detail.at[idx, 'organization_id'] = user_events.iloc[0]['value']

    new_users_detail['organization_name'] = new_users_detail['organization_id'].map(org_map)

    total_new_users = len(new_users_detail)
    users_in_orgs = new_users_detail['organization_id'].notna().sum()
    individual_users = total_new_users - users_in_orgs

    percent_users_in_orgs = (users_in_orgs / total_new_users) * 100
    percent_individual_users = (individual_users / total_new_users) * 100

    active_users = events_df[(events_df['category'] == 'workspace') & (events_df['name'] == 'enter')]
    active_users_per_week = active_users.groupby('week')['user_id'].nunique()

    top_active_users = active_users.groupby(['week', 'user_id']).size().reset_index(name='counts')
    top_active_users_per_week = top_active_users.sort_values(['week', 'counts'], ascending=[True, False]).groupby('week').head(10)

    top_active_users_per_week['organization_id'] = top_active_users_per_week.apply(
        lambda row: events_df[(events_df['user_id'] == row['user_id']) & (events_df['category'] == 'workspace') & (events_df['name'] == 'enter') & (events_df['user_id'] != events_df['value'])]['value'].values[0] 
        if not events_df[(events_df['user_id'] == row['user_id']) & (events_df['category'] == 'workspace') & (events_df['name'] == 'enter') & (events_df['user_id'] != events_df['value'])].empty else None,
        axis=1
    )
    top_active_users_per_week['organization_name'] = top_active_users_per_week['organization_id'].map(org_map)

    individual_new_users = new_users_detail[new_users_detail['organization_id'].isna()]
    individual_usage_events = events_df[events_df['user_id'].isin(individual_new_users['user_id']) & (events_df['category'] == 'workspace') & (events_df['name'] == 'enter')]
    individual_usage_duration = individual_usage_events.groupby('user_id')['created'].apply(lambda x: x.max() - x.min()).mean()

    active_orgs = active_users[active_users['user_id'] != active_users['value']]
    active_orgs_per_week = active_orgs.groupby('week')['value'].nunique()

    top_active_orgs = active_orgs.groupby(['week', 'value']).size().reset_index(name='counts')
    top_active_orgs_per_week = top_active_orgs.sort_values(['week', 'counts'], ascending=[True, False]).groupby('week').head(10)
    top_active_orgs_per_week['organization_name'] = top_active_orgs_per_week['value'].map(org_map)

    current_date = pd.to_datetime('today')
    active_orgs = active_orgs[active_orgs['value'].apply(lambda x: expiration_map.get(x, current_date + pd.DateOffset(days=1)) >= current_date if pd.notna(expiration_map.get(x)) else False)]

    org_activity = active_orgs.groupby('value').size()
    healthy_orgs = org_activity[org_activity > org_activity.median()].index.tolist()
    less_active_orgs = org_activity[org_activity <= org_activity.median()].index.tolist()

    healthy_orgs_names = [org_map[org] for org in healthy_orgs if org in org_map]
    less_active_orgs_names = [org_map[org] for org in less_active_orgs if org in org_map]

    return jsonify({
        "new_users_per_week": new_users_per_week.to_dict(),
        "percent_users_in_orgs": percent_users_in_orgs,
        "percent_individual_users": percent_individual_users,
        "active_users_per_week": active_users_per_week.to_dict(),
        "top_active_users_per_week": top_active_users_per_week.to_dict(),
        "individual_usage_duration": individual_usage_duration.total_seconds(),
        "active_orgs_per_week": active_orgs_per_week.to_dict(),
        "top_active_orgs_per_week": top_active_orgs_per_week.to_dict(),
        "healthy_orgs_names": healthy_orgs_names,
        "less_active_orgs_names": less_active_orgs_names
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
