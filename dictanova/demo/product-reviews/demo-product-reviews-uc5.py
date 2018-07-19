# -*- coding: utf-8 -*-

"""
This script implements the fourth use case:
Attention points per brand.
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
	
	#################################### TOP NEGATIVE OPINIONS FROM DETRACTORS PER BRAND
	query = {
		"type": "COUNT",
		"field": "createdAt",
		"query": {
			"field": "metadata.recommande",
			"operator": "EQ",
			"value": "Ne recommande pas"
		},
		"dimensions": [{
				"field": "metadata.marque",
				"group": "DISTINCT"
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 10
			}, {
				"field": "TERMS_POLARITY",
				"group": "NEGATIVE"
			}
		]
	}
	print("Query:")
	print(json.dumps(query, indent=4, sort_keys=False))
	# Requests
	r = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b2286583a35940001399b1a/documents",
		json=query,
		auth=dictanova_auth)
	print(r)
	
	##################################################################### PREPARE RESULTS
	# Build dataframe
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df = df[df["volume"] > 0] # remove null
	df["brand"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df.drop(columns=["dimensions"], inplace=True)
	df.sort_values(by=["brand", "value"], axis="index", ascending=False, inplace=True)

	##################################################################### DISPLAY RESULTS
	# Word cloud
	# pip3 install wordcloud
	import math
	from wordcloud import WordCloud
	import matplotlib.pyplot as plt
	from matplotlib import colors
	onlyred = colors.ListedColormap(['orangered'])
	brands = list(df["brand"].unique())
	row = math.ceil(math.sqrt(len(brands)))
	col = math.floor(math.sqrt(len(brands)))
	fig, axis = plt.subplots(row, col)
	fig.tight_layout()
	for i, brand in enumerate(brands):
		# Pretty print results
		print("Attention points for brand '%s':" % brand)
		print(df[df["brand"]==brand])
		# Compute word distribution for wordcloud
		wc_freq = {row.opinion:row.volume for row in df[df["brand"]==brand].itertuples()}
		wc = WordCloud(
			prefer_horizontal=1, 
			font_path='Geomanist-Regular.otf',
			background_color="white", 
			colormap=onlyred)
		wordcloud = wc.fit_words(wc_freq)
		# Add to subfig
		r = i//col
		c = i%col
		axis[r][c].imshow(wordcloud)
		axis[r][c].set_title(brand)
		axis[r][c].axis("off")
	# Render
	plt.show()
	
	