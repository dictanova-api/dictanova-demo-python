# -*- coding: utf-8 -*-

"""
This script implements the first use case:
Top negative opinions of reviews from 2016 that do not recommand a product from subcategory "Couches Bébé".
"""

import pandas as pd
import requests, json
import numpy as np
import sys

class DictanovaAPIAuth(requests.auth.AuthBase):
	"""Attaches Dictanova Bearer Authentication to the given Request object."""
	
	def __init__(self, id, secret):
		self.apiclient_id = id
		self.apiclient_secret = secret
		self._token = None
	
	def __eq__(self, other):
		return all([
			self.apiclient_id == getattr(other, 'apiclient_id', None),
			self.apiclient_secret == getattr(other, 'apiclient_secret', None)
		])
	
	def __ne__(self, other):
		return not self == other
	
	def __call__(self, r):
		r.headers['Authorization'] = self.get_token()
		return r
	
	def get_token(self):
		# Get authentication token
		if self._token is None:
			payload = {
				"clientId": self.apiclient_id,
				"clientSecret": self.apiclient_secret
			}
			r = requests.post("https://api.dictanova.io/v1/token", json=payload)
			self._token = r.json()
		# Always use the one in cache
		return "Bearer %s" % self._token["access_token"]

if __name__ == "__main__":
	# Prepare Auth handler with API client id and secret
	# https://docs.dictanova.io/docs/authentication-and-security
	clientId, clientSecret = open("../credentials", "r").readline().strip().split(";")
	dictanova_auth = DictanovaAPIAuth(clientId, clientSecret)
	
	####################################################################### TOP OPINION
	# Query for top opinions
	query = {
		"operator": "AND",
		"criteria": [{
			# Between 1/1/2016 and 31/12/2016
			"field": "metadata.depot_date",
			"operator": "GTE",
			"value": "2016-01-01T00:00:00Z"
		}, {
			"field": "metadata.depot_date",
			"operator": "LTE",
			"value": "2016-12-31T00:00:00Z"
		}, {
			# Only subcategory "Couches Bébé"
			"field": "metadata.subcategory",
			"operator": "EQ",
			"value": "Couches Bébé"
		}, {
			# Do not recommand
			"field": "metadata.recommande",
			"operator": "EQ",
			"value": "Ne recommande pas"
		}]
	}
	print("Query:")
	print(json.dumps(query, indent=4, sort_keys=False))
	
	# Request
	r = requests.post(
		"https://api.dictanova.io/v1/search/datasets/5b2286583a35940001399b1a/terms?opinions=NEGATIVE",
		json=query,
		auth=dictanova_auth)
	print(r)
	
	# Pretty print results
	print("Top negative opinions of detractors in 2016 about subcategory 'Couches Bébé'")
	for i,opinion in enumerate(r.json()['items']):
		print("#%02d [%2d occ.]\t%s" % (i+1, opinion["occurrences"], opinion["label"]))
	
	# Word cloud
	# pip3 install wordcloud
	from wordcloud import WordCloud
	import matplotlib.pyplot as plt
	from matplotlib import colors
	onlyred = colors.ListedColormap(['orangered'])
	wc_freq = {opinion["label"]:opinion["occurrences"] for opinion in r.json()['items']}
	wc = WordCloud(
		prefer_horizontal=1, 
		font_path='/Users/Fabien/Library/Fonts/Geomanist-Regular.otf',
		background_color="white", 
		colormap=onlyred)
	wordcloud = wc.fit_words(wc_freq)
	plt.imshow(wordcloud)
	plt.axis("off")
	plt.show()
	
	####################################################################### SEARCH
	# Search for most common opinion
	most_common_opinion = r.json()['items'][0]
	print("Search for most common negative opinion '%s'" % most_common_opinion["label"])
	query = {
		"operator": "AND",
		"criteria": [{
			# Between 1/1/2016 and 31/12/2016
			"field": "metadata.depot_date",
			"operator": "GTE",
			"value": "2016-01-01T00:00:00Z"
		}, {
			"field": "metadata.depot_date",
			"operator": "LTE",
			"value": "2016-12-31T00:00:00Z"
		}, {
			# Only subcategory "Couches Bébé"
			"field": "metadata.subcategory",
			"operator": "EQ",
			"value": "Couches Bébé"
		}, {
			# Do not recommand
			"field": "metadata.recommande",
			"operator": "EQ",
			"value": "Ne recommande pas"
		}, {
			# With most common negative term
			"field": "TERMS",
			"operator": "EQ",
			"value": most_common_opinion["id"],
			"opinion": "NEGATIVE"
		}]
	}
	
	# Request
	r = requests.post(
		"https://api.dictanova.io/v1/search/datasets/5b2286583a35940001399b1a/documents",
		json=query,
		auth=dictanova_auth)
	print(r)
	
	# Pretty print results
	print("%d reviews from detractors of 2016 in subcategory 'Couches Bébé' negative about '%s'" %\
		(r.json()["total"], most_common_opinion["label"]))
	for i,doc in enumerate(r.json()["items"]):
		# identify occurrences
		highlights = [o for o in doc["enrichments"] if (o["term"]==most_common_opinion["id"] and o["opinion"]=="NEGATIVE")]
		highlights = sorted(highlights, key=lambda h: h["offset"]["begin"])
		splitted = []
		last=0
		for highlight in highlights:
			splitted.append( doc["content"][last:highlight["offset"]["begin"]] )
			splitted.append( doc["content"][highlight["offset"]["begin"]:highlight["offset"]["end"]] )
			last=highlight["offset"]["end"]
		splitted.append(doc["content"][last:])
		print("###### Review %d/%d" % (i+1, r.json()["total"]))
		print("**".join(splitted))
		print()
	
	