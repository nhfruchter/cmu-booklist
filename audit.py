from auth import authenticate
from BeautifulSoup import BeautifulSoup
from itertools import groupby, chain
import re
import string
import copy

def tag_contains(rawdata, value):
    return [el.text for el in rawdata if value in el.text][0]    
        
def flatten(i):
    """Turn something like [a, b, [c, d], e] into [a,b,c,d,e]."""
    
    iterable = reduce(list.__add__, i)
    can_flatten = [list, tuple]                
    for el in iterable:
        if type(el) in can_flatten:
            yield el[0].strip()
        else:
            yield el.strip()      

class RequirementList(object):
    def __init__(self, name):
        self.name = name
        self.courses = []
    
    def add(self, c): 
        self.courses.append(c)    
        
    def __str__(self):
        return "{} with {} reqs".format(self.name, len(self.courses))
    
    def __repr__(self):
        return str(self)
    
    @property
    def all_warnings(self):
        return [c for c in self.courses if type(c) == UnfilledCourse]

    @property
    def all_courses(self):
        return [c for c in self.courses if type(c) == Course]    
        
    @property
    def not_completed(self):
        return sum(not c.fulfilled for c in self.all_courses) + len(self.all_warnings)
    
    @property
    def in_progress(self):
        return [c for c in self.all_courses if c.in_progress ]
        
    @property    
    def warning_summary(self):
        warnings = []
        if self.all_warnings:
            for wtype, nwarns in groupby(self.all_warnings, lambda w: w.warning[1]): 
                
                warnings.append( "{} {}".format(sum(float(w.warning[0]) for w in nwarns), wtype) )
        if self.not_completed:
            warnings.append("({} in progress)".format(len(self.in_progress)))
        if warnings:
            return ", ".join(warnings)
        else:    
            return False    
            

class Course(object):
    def __init__(self, i, name, number, semester, year, grade, units, fulfilled):
        self.i = i
        self.name = name
        self.number = number
        self._semester = (semester, year)
        self.grade = grade
        self.units = units
        self.fulfilled = fulfilled

    @property
    def semester(self):
        return " ".join(self._semester)
        
    @property
    def in_progress(self):
        return self.grade == "*"    
        
    def __str__(self):
        base = "{} {} ({} units) - {} - {} - {}".format(self.number, self.name, self.units, self.grade, self.semester, self.fulfilled)        
        return base
        
    def __repr__(self): return str(self)
    
class UnfilledCourse(Course):    
    def __init__(self, name, warning):
        self.name = name
        self.warning = warning
    
    def __str__(self):
        return "{} - {}".format(self.name, self.warning)    
    
def academicaudit(user, pw):
    # Authenticate and grab home page
    _audit_base = "http://enr-apps.as.cmu.edu/audit/audit"
    try:
        session = authenticate('https://enr-apps.as.cmu.edu/audit/audit', user, pw)
    except:
        raise Exception("Failed to log in.")
    
    homepage = BeautifulSoup(session.get('{}?call=2'.format(_audit_base)).content)
    
    # Figure out the correct attributes for the URL
    major = homepage.find('input', attrs={'name':'MajorFile'}).get('value')
    
    # Build URL
    auditurl = "{}?call=7&MajorFile={}".format(_audit_base, major)            

    # Now, parse the content of the audit
    return parse_raw_audit(session.get(auditurl).content)
    
def auditfromstring(s):
    return parse_raw_audit(s, kind="text")
    
class Audit(object):
    def __init__(self, courses, unused, unit_qpa, name):
        self.courses = courses
        self.unused = unused
        self.unit_qpa = unit_qpa
        self.name = name
        
    def all_courses(self):
        groups = copy.copy(self.courses) + [self.unused]
        for g in groups:
            for course in g.courses:                
                if hasattr(course, 'grade'):
                    yield course 
        
def parse_raw_audit(audit, kind="html"):
    def parse_unused(data):
        # (number, semester, year, grade, units)
        re_unused = re.compile(r"([0-9]{2}\-[0-9]{3}) (\w+) * \'([0-9]{2})\s+([a-z]+|\*)\s+(.+)$", re.IGNORECASE) 
        
        r = RequirementList("Unused")
        for line in data.splitlines():
            line = line.strip()
            if line:
                number, semester, year, grade, units = re_unused.match(line).groups()
                fulfilled = "*" not in grade
                r.add(Course(None, None, number, semester, year, grade, units, fulfilled))
            
        return r    
    
    def parse_units_qpa(data):
        data = data.strip()
        items = [ map(lambda s: s.strip(), line.split(":")) for line in data.split("\n")]
        return dict(items)
        
    def parse_courses(data):         
        # Regular expressions for matching audit line parts
        # (i, name)
        re_coursename = re.compile(r"([0-9]?[0-9])\. (.+)$", re.IGNORECASE) 
        # (number, semester, year, grade, units)
        re_courseinfo = re.compile(r"([0-9]{2}\-[0-9]{3}) (\w+) * \'([0-9]{2})\s+([a-z]+|\*)\s+(.+)$", re.IGNORECASE) 
        # (n, course|units)
        re_unfilled = re.compile(r"(.+)\s+unfilled\s+(\w+)", re.IGNORECASE)
        # no groups, just a match
        re_isname = re.compile(r"\d+\.\s+")
                    
        def parse_seg(seg):
            """Parse one audit segment (basically a line)."""
            courses = []

            for part in seg:
                if re_isname.match(part):
                    # If this contains a requirement name
                    i, name = re_coursename.match(part).groups()
                    name = name.replace("_", " ")
                elif re_unfilled.match(part):
                    # If this talks about an unfilled requirement
                    missing = re_unfilled.match(part).groups()
                    courses.append(UnfilledCourse(name, missing))
                else:
                    # Otherwise, it's course info
                    number, semester, year, grade, units = re_courseinfo.match(part).groups()
                    fulfilled = "*" not in grade
                    course = Course(i, name, number, semester, year, grade, units, fulfilled)
                    courses.append(course)     
            return courses              

        # "Sides" of the audit output are split by colons
        lines = [ line.split(" :") for line in data.splitlines() if line ]
        courses = []

        # Segment the list by number
        for chunk in lines:
            with_previous = chunk[0].startswith(" "*20) and len(chunk) == 1
            extra_text = chunk[0][0].strip() in string.ascii_letters
            if with_previous:
                courses[-1].append(chunk)
            elif not with_previous or extra_text:
                courses.append(chunk)           
        courses = groupby(courses, lambda i: len(i) > 1)

        # Turn the list into Course objects and headings
        sections = []
        for is_course, c_iter in courses:
            # Headings
            c = list(flatten(list(c_iter)))
            if not is_course: 
                # Notes will show up as subsequent elements in the list of line segs
                # past the initial portion
                has_note = len(c) > 1 and bool(" ".join(c).strip())                    
                reqlist = RequirementList(c[0])
                if has_note:
                    reqlist.notes = " ".join(n.strip() for n in c[1:])
                sections.append(reqlist)    
            else:
                sections[-1].courses = parse_seg(c)
                        
        return sections

    if kind == "html":
        # Find relevant text blocks
        parser = BeautifulSoup(audit)
        rawdata = parser.findAll('pre')
    
        name = parser.find('h3').text
        unit_qpa = parse_units_qpa(tag_contains(rawdata, "UNIT_INPRG"))
        courses = parse_courses(tag_contains(rawdata, "1."))
        unused = parse_unused(tag_contains(rawdata, "(Unused)"))
        
    elif kind == "text":
        # Split the input at these locations
        tokens = dict(
            header=audit.index("Course-Requirement Matchings"),
            unused=audit.index("Not Matched:"),
            info=audit.index("ANDREW_ID:"),
            end=audit.index("Notes:")
        )
        header = audit[0:tokens['header']].splitlines()

        name = [line for line in header if line == line.upper() and line][0]
        
        # Turn into the plaintext blocks that the parser expects
        unit_qpa = '\n'.join(audit[tokens['info']:tokens['end']].splitlines()[1:])
        courses = '\n'.join(audit[tokens['header']:tokens['unused']].splitlines()[1:])
        unused = '\n'.join(audit[tokens['unused']:tokens['info']].splitlines()[1:])
        unit_qpa = parse_units_qpa(unit_qpa)
        courses = parse_courses(courses)
        unused = parse_unused(unused)

    return Audit(courses, unused, unit_qpa, name)
