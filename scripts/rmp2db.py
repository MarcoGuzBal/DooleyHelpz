from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pandas as pd
import json


if __name__ == "__main__":

# 1. csv to json
    csv_path = "data/rmp.csv"
    df = pd.read_csv(csv_path)
    df = df.drop(columns=[
        "cardfeedback__cardfeedbackitemlq6nix1", 
        "cardfeedback__cardfeedbackitemlq6nix14",
        "cardschool__schoolsc19lmz2k1"
    ], errors="ignore")

    df = df.rename(columns={
        "professor": "name",
        "Title_URL": "url",
        "rating": "rating",
        "numRating": "num_ratings",
        "Department": "department",
        "cardfeedback__cardfeedbackitemlq6nix13": "would_take_again_%",
        "cardfeedback__cardfeedbackitemlq6nix15": "difficulty"
    })
    
    
    
    # convert num_ratings to int
    try:
        for i in range(100):
            val = df.at[i, "num_ratings"]
            val = str(val).strip()
            val = val.split()[0]  # take only the first part if there are extra words
            df.at[i, "num_ratings"] = int(val)
            
            # print(df.at[i, "num_ratings"])
    except Exception as e:
        print(f"Error converting 'num_ratings': {e}")

    print("converted num_ratings to int")

    # convert would_take_again_% to int
    try:
        for i in range(len(df)):
            val = df.at[i, "would_take_again_%"]
            # print(val)
            if pd.isna(val): 
                df.at[i, "would_take_again_%"] = None
            else:
                val = str(val).strip()
                if val.endswith("%"):
                    val = val[:-1]
                    df.at[i, "would_take_again_%"] = int(val)
            # print(df.at[i, "would_take_again_%"])
    
    except Exception as e:
        print(f"Error converting 'would_take_again_%': {e}")
    
    print("converted would_take_again_% to int")

    # convert difficulty to float
    try:
        for i in range(len(df)):
            val = df.at[i, "difficulty"]
            if pd.isna(val):
                df.at[i, "difficulty"] = None
            else:
                val = str(val).strip()
                df.at[i, "difficulty"] = float(val)
            
            # print(df.at[i, "difficulty"])
    except Exception as e:
        print(f"Error converting 'difficulty': {e}")

    print("converted difficulty to float")

    data = df.to_dict(orient="records")
    print("converted csv to dict")
  
# 2. connect to Ratings collection and insert
    load_dotenv()
    uri = os.getenv("DB_URI")
    client = MongoClient(uri) #cluster
    db = client["RateMyProfessors"] # database
    col = db["Professors"] #collection
    print("connected the Professors collection")

    col.insert_many(data)

# 3. create indexes
    col.create_index("url", unique=True)
    print("created index on url")
    col.create_index("name")
    print("created index on name")