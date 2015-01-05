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
        
def cachekey(cid, instructor):
    return str(hash("{}{}".format(cid, instructor)))
    
        
def check(cache, mapping, cidlist):
    cache = set()
    nocache = set()
    
    for cid in cidlist:
        cidstring = "".join(cid)
        try:
            sections = mapping['depts'][cid[0]]['courses'][cidstring]
        except KeyError:
            continue    
        for section in sections:
            instructor = section['instructor']
            key = cachekey(cidstring, instructor)
            if not CACHE.get(key):
                nocache.add(cidstring)                    
                break
            
            cache.add(cidstring)    
            
    return list(cache), list(nocache)
    
def store(cache, info):
    cid = info['name'].split(" ")[-1].replace("-", "")
    key = cachekey(cid, info['instructor'])
    if key not in cache:
        cache[key] = info
    
def retrieve(cache, cid, verba):
    result = []
    for section in verba:
        key = cachekey(cid, section['instructor'])
        result.append(cache.get(key))
    return result    
    
CACHE = getmemcache()