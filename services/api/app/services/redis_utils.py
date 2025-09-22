import redis
import datetime, os

def write_universe_to_redis(universe_df):
    # create keys
    today = datetime.date.today().strftime("%Y-%m-%d")
    zkey_today = f"universe:{today}"
    zkey_latest = "universe:latest"

    # create instance of Redis Server
    r = redis.Redis(host=os.environ.get("REDIS_HOST", "127.0.0.1"), port=6379, db=0)
    
    # create pipeline for atomic transactions
    pipe = r.pipeline(transaction=True)

    # delete any previous keys to avoid confusion
    pipe.delete(zkey_latest)

    # add transactions to ZSET by iterating over universe_df
    for _, rows in universe_df.iterrows():
        token = str(rows["instrument_token"])
        score = float(rows["score"])
        pipe.zadd(zkey_today, {token:score})
    
    # execute the pipeline to commit the transaction to Redis DB
    pipe.execute()

    # create another copy of the ZSET for archival
    members = r.zrange(zkey_today,0,-1,withscores=True)
    if members:
        pipe = r.pipeline(transaction=True)
        for member,score in members:
            pipe.zadd(zkey_latest, {member:score})
    
    # create TTL 
    pipe.expire(zkey_today, 60*60*36) # expires after 36 hours
    pipe.expire(zkey_latest, 60*60*12) # expires after 12 hours
    pipe.execute()
    




    