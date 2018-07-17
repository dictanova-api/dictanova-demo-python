# -*- coding: utf-8 -*-

"""
This script implements the third use case:
Top brands in satisfaction regarding leaks.
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
	
	####################################################################### LIST OPINIONS
	# Query for opinions containing "fuite"
	# Requests
	r = requests.post(
		"https://api.dictanova.io/v1/search/datasets/5b2286583a35940001399b1a/terms?q=fuite",
		auth=dictanova_auth)
	print(r)
	
	all_leaks = [o["id"] for o in r.json()["items"]]
	print("Identified %d variations around 'fuite'" % len(all_leaks))
	
	####################################################################### AGGREGATION
	# Query for CSAT
	query = {
		"type" : "CSAT",
		"field" : "metadata.note_moyenne",
		"query" : {
			"operator": "AND",
			"criteria": [
				{
					"field": "metadata.subcategory",
					"operator": "EQ",
					"value": "Couches Bébé"
				},
				{
					"field" : "TERMS",
					"operator" : "IN",
					"value" : all_leaks
				},
			]
		},
		"dimensions" : [
			{
				"field" : "metadata.marque",
				"group" : "DISTINCT"
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

	# Format results into a dataframe
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df["brands"] = df["dimensions"].apply(lambda x: x[0])
	df.sort_values(by="value", axis="index", ascending=False, inplace=True)
	df.set_index("brands", inplace=True)
	
	# Pretty print results and plot
	print("Top brands by satisfaction regarding leaks")
	print(df[["value", "volume"]])

	