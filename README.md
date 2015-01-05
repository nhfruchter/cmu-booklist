# CMU textbook list generator

Has being lazy ever motivated you to do way too much work? This is basically that. Log in with your Andrew ID or specify some course numbers and get a list of textbooks in return, instead of having to hunt through the textbook comparison website.

* `app.py` is the Flask web front end.
* `auth.py` handles logging in to CMU's protected resources.
* `audit.py` is borrowed from my [academic audit parser](https://github.com/nhfruchter/cmu-acadaudit), which is also how the program gets a list of your upcoming courses.
* `bookcache.py` helps with caching information so we don't hit the textbook comparison site over and over.
* `booklist.py` does everything else, namely translating between the textbook comparison site's class IDs and CMU class IDs which unfortunately aren't the same.

Live at http://cmu-textbooks.herokuapp.com.
