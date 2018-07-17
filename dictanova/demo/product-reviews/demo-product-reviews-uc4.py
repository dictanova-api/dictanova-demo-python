# -*- coding: utf-8 -*-

"""
This script implements the fourth use case:
Llosa matrix for diapers. Compute CSAT for each opinion.
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
	
	################################################################ TOP POLARIZED TERMS
	query = {
		"field": "metadata.subcategory",
		"operator": "EQ",
		"value": "Couches Bébé"
	}
	# Get top positive and negative opinions
	r_pos = requests.post(
		"https://api.dictanova.io/v1/search/datasets/5b2286583a35940001399b1a/terms?opinions=POSITIVE",
		json=query,
		auth=dictanova_auth)
	r_neg = requests.post(
		"https://api.dictanova.io/v1/search/datasets/5b2286583a35940001399b1a/terms?opinions=NEGATIVE",
		json=query,
		auth=dictanova_auth)
	top_pos = {op["id"]:op["occurrences"] for op in r_pos.json()["items"]}
	top_neg = {op["id"]:op["occurrences"] for op in r_neg.json()["items"]}
	top_polarized = [op for op in top_pos if op in top_neg]
	print("Selected %d top opinions: %s" % (len(top_polarized), ",".join(top_polarized)))
	
	############################################################ COMPUTE CSAT PER OPINION
	csat = {}
	query = {
		"type": "CSAT",
		"field": "metadata.note_moyenne",
		"query": {
			"operator": "AND",
			"criteria": [
				{
					"field": "metadata.subcategory",
					"operator": "EQ",
					"value": "Couches Bébé"
				}, {
					"field": "TERMS",
					"operator": "EQ",
					"value": None
				}
			]
		}
	}
	for opinion in top_polarized:
		# Build specific query
		print("Query for %s:" % opinion)
		query["query"]["criteria"][1]["value"] = opinion
		print(json.dumps(query, indent=4, sort_keys=False))	
		# Requests
		r = requests.post(
			"https://api.dictanova.io/v1/aggregation/datasets/5b2286583a35940001399b1a/documents",
			json=query,
			auth=dictanova_auth)
		print(r)
		# Add results
		csat[opinion] = r.json()["periods"][0]["total"]["value"]
	
	##################################################################### PREPARE RESULTS
	# Build dataframe
	df = pd.concat([
			pd.DataFrame.from_dict(csat, orient="index"),
			pd.DataFrame.from_dict(top_pos, orient="index"),
			pd.DataFrame.from_dict(top_neg, orient="index")
		], axis="columns", join='inner')
	df.columns = ["csat", "vol_pos", "vol_neg"]
	# Compute polarity ratio
	df["polarity_vol"] = df["vol_pos"] + df["vol_neg"]
	df["polarity_ratio"] = (df["vol_pos"] / df["polarity_vol"]) - (df["vol_neg"] / df["polarity_vol"])
	
	##################################################################### DISPLAY RESULTS
	
	# Pretty print results
	print("Relation between polarity and satisfaction score on top opinions:")
	print(df)
	
	# Plot
	df["color"] = df["polarity_ratio"].apply(lambda x: {False: "orangered", True: "green"}[x>=0])
	import matplotlib.pyplot as plt
	ax = df.plot.scatter(
		x="polarity_ratio",
		y="csat", 
		s=df["polarity_vol"].values, # https://github.com/pandas-dev/pandas/issues/8244
		c=df["color"],
		alpha=0.5)
	for row in df.iterrows():
		ax.annotate(row[0], (row[1]["polarity_ratio"], row[1]["csat"]))
	plt.show()
	
	