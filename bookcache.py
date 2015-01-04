import pylibmc
import os

def getmemcache():    
    servers = os.environ.get('MEMCACHIER_SERVERS', None)
    user = os.environ.get('MEMCACHIER_USERNAME', '')
    pw = os.environ.get('MEMCACHIER_PASSWORD', '')
    
    if servers and servers[0] != '':
        # Probably heroku/production
        servers = servers.split(',')
        return pylibmc.Client(servers, binary=True,
                    username=user, password=pw,
                    behaviors={"tcp_nodelay": True,
                               "ketama": True,
                               "no_block": True,})

    else:
        # Local instance of Memcache (not heroku)
        servers = ['127.0.0.1:11211'] 
        return pylibmc.Client(servers, binary=True)

def cacheisactive(mc):
    try:
        return bool(mc.get_stats())
    except:
        return False    
        
def check(cache, cidlist):
    cache = []
    nocache = []
    
    for cid in cidlist:
        cid = "".join(cid)
        if CACHE.get(cid):
            cache.append(cid)
        else:
            nocache.append(cid)    
            
    return cache, nocache
    
def store(cache, info):
    key = info['name'].split(" ")[-1].replace("-", "")
    if key not in cache:
        cache[key] = info
    
CACHE = getmemcache()