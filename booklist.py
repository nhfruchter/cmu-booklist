import requests
import json
import pickle
import os

# Memcache backend
import bookcache as _c

# CMU academic audit parser
import audit

# JS parser
from slimit.parser import Parser
from slimit.visitors import nodevisitor
from slimit.visitors.nodevisitor import ASTVisitor

# HTML parser
from BeautifulSoup import BeautifulSoup

def jsonget(url):
    return json.loads(requests.get(url).content)

def upcoming_courses(aud):
    """Return a list of course IDs for the upcoming semester."""
    
    courses = [c for c in aud.all_courses() if c.grade == u"*"]
    return [c.number.replace("-", "") for c in courses]

def parse_mapping(term):
    def extract_cid(dept, verba_id):
        # e.g. id = 'BUS ADMIN76-101' => '76-101' => '76101' => '76'
        return verba_id.replace(dept, "").replace("-", "").strip()
        
    URL = "http://cmu.verbacompare.com/compare/departments/?term={}".format(term)
    CROSSLIST_DELIMITER = "/"
    
    verba_prefixes = jsonget(URL)
    
    mapping = {
        'term': term,
        'depts': {}
    }
            
    for dept in verba_prefixes:
        verba_id = dept['id']
        verba_name = dept['name']

        courselist_URL = "http://cmu.verbacompare.com/compare/courses/?id={}&term_id={}".format(verba_id, term)
        courselist = jsonget(courselist_URL)
        
        cmu_prefix = extract_cid(verba_name, courselist[0]['id'])[0:2]        
        print "Scraping {} - {}".format(cmu_prefix, verba_name)
        
        mapping['depts'][cmu_prefix] = {
            'verba_id': verba_id,
            'verba_name': verba_name,
            'courses': {}
        }
        
        for c in courselist:
            cid = extract_cid(verba_name, c['name'])

            # Cross-listed notation: add another entry
            if CROSSLIST_DELIMITER in cid:
                crosslist_cid = cid[0:2] + cid[cid.index(CROSSLIST_DELIMITER)+1:]
                original_cid = cid[0:5]
                mapping['depts'][cmu_prefix]['courses'][original_cid] = c['sections']
                mapping['depts'][cmu_prefix]['courses'][crosslist_cid] = c['sections']
            else:    
                mapping['depts'][cmu_prefix]['courses'][cid] = c['sections']
            
    return mapping        

def parse_cid(cid):
    """Parse a CMU course ID into a (department, id) tuple."""
    cid = str(cid).replace("-", "").replace(" ", "").strip()
    
    if len(cid) == 5:
        return (cid[0:2], cid[2:])
    else:
        raise ValueError("This course ID doesn't seem to be valid.")
        
def get_mapping(term):
    """Generate a verbacompare course info mapping."""    
    DB = "coursemapping.pickle"    
    
    if not os.path.exists(DB):
        # Generate mapping if it doesn't exist
        mapping = parse_cid(term)
        with open(DB, 'w') as f:
            pickle.dump(mapping, f)
    else:
        # Otherwise, load from the pickle
        with open(DB) as f:
            mapping = pickle.load(f)
            
    return mapping
            
def cmu_to_verba(mapping, cid):
    """Get a list of books for a course ID `cid`."""

    BASE = "http://cmu.verbacompare.com/"
    TERM = 6668 # The "term" (semester ID?), currently S15
    cid = parse_cid(cid)
    
    # Get the verbacompare ID
    try:
        sections = mapping['depts'][cid[0]]['courses']["".join(cid)]
    except KeyError:
        return False
        
    return sections
    
class ObjVisitor(ASTVisitor):
    def __init__(self, *args, **kwargs):
        super(ObjVisitor, self).__init__(*args, **kwargs)
        self.vardump = []
    
    def visit_Object(self, node):
        self.vardump.append(node.to_ecma())
                
def get_books(mapping, cidlist):
    """Return a list of courses with instructor and book info."""
    havecache = _c.cacheisactive(_c.CACHE)

    # Don't want to keep hammering their servers, so check if available
    if havecache:
        cache, nocache = _c.check(_c.CACHE, [parse_cid(cid) for cid in cidlist])

    BASE = "http://cmu.verbacompare.com/comparison?id={}"
    
    # If cache is available, still need to check for uncached stuff
    if havecache:
        sections = [cmu_to_verba(mapping, cid) for cid in nocache]
    else:    
        sections = [cmu_to_verba(mapping, cid) for cid in cidlist]                    
    sections = [s for s in sections if s != False]
    
    verba_info = [cmu_to_verba(mapping, cid) for cid in cidlist]                    
    verba_info = [s for s in verba_info if s != False]
    
    if verba_info:
        verba_ids = [section['id'] for section in reduce(list.__add__, verba_info)]
        URL = BASE.format(",".join(verba_ids))
    
        if sections:    
            # Download and parse if needed        
            parser = BeautifulSoup(requests.get(URL).content)
            raw_data = [el.getText() for el in parser.findAll("script")
                         if 'Verba.Compare' in el.getText()][0] 
             
            # Parse the extracted JS into an AST to extract the correct variable
            tree = Parser().parse(raw_data)
            objects = ObjVisitor()
            # Oh god why
            objects.visit(tree)

            # Finally
            data = [json.loads(d) for d in [i for i in objects.vardump if "isbn" in i]]

        # Bring in the cached data if it exists, otherwise just initialize empty result
        if havecache and cache:
            summary = {
                'url': URL,
                'courses': [_c.CACHE.get(cid) for cid in cache]
            }
        else:        
            summary = {
                'url': URL,
                'courses': []
            }
    
        # If we had to grab anything, now put it into the result
        if sections:
            for course in data:
                if course.get('title') and course.get('instructor'):
                    info = {
                        'name': course['title'],
                        'instructor': course['instructor'],
                        'books': []
                    }
                    if 'books' in course:
                        for book in course['books']:
                            bookinfo = {
                                'title': book['title'],
                                'author': book['author'],
                                'isbn': book['isbn'],
                                'citation': book['citation'],
                                'required': book['required'].lower() == 'required',
                            }
                            info['books'].append(bookinfo)                
                
                summary['courses'].append(info)
            
                if havecache:
                    # Store in cache for future use
                    _c.store(_c.CACHE, info)
    
        return summary    
        