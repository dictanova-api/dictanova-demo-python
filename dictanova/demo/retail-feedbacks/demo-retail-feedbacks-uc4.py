# -*- coding: utf-8 -*-

"""
UC#04: Detailed NPS
What's behind my NPS
"""

import pandas as pd
import requests, json, re, sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors

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

	################################################ NPS PER TOP OPINION
	print("NPS per top opinion")
	print("\tquery")
	# Compute the NPS for the top 10 opinions
	query = {
		"type": "NPS",
		"field": "metadata.rating_nps",
		"dimensions": [
			{
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 10
			}
		]
	}
	r = requests.post(
			"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
			json=query,
			auth=dictanova_auth)
	print("\t%s"%r)
	# Load in pandas
	print("\tprepare")
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df["opinion"] = df["dimensions"].apply(lambda x: x[0])
	df["var_nps"] = df["value"] - r.json()["periods"][0]["total"]["value"]
	df.sort_values("value", ascending=True, inplace=True)
	# Plot absolute NPS
	print("\trender absolute")
	df.plot.barh(
		x="opinion", y="value",
		title="NPS for top 10 opinions",
		colormap=colors.ListedColormap(['darkblue'])
	)
	plt.savefig("uc4-nps-per-top10-opinions.png")
	plt.show()
	# Plot var NPS
	print("\trender variations")
	df.plot.barh(
		x="opinion", y="var_nps",
		title="Variation with global NPS for top 10 opinions",
		colormap=colors.ListedColormap(['darkblue'])
	)
	plt.savefig("uc4-nps-variation-per-top10-opinions.png")
	plt.show()

	########################################### NPS DETAILS PER TOP OPINION
	# Compute the NPS detail for the top 10 opinions
	print("NPS detail per top opinion")
	print("\tquery")
	query = {
		"type": "NPS",
		"field": "metadata.rating_nps",
		"dimensions": [
			{
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 10
			}, {
				"field": "metadata.rating_nps",
				"group": "NPS_GROUP"
			}
		]
	}
	r = requests.post(
			"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
			json=query,
			auth=dictanova_auth
	)
	print("\t%s"%r)
	# Load in pandas
	print("\tprepare")
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df["opinion"] = df["dimensions"].apply(lambda x: x[0])
	df["nps_range"] = df["dimensions"].apply(lambda x: x[1])
	df = df.pivot_table(index="opinion", columns="nps_range", values="volume")
	df.fillna(0, inplace=True) # nan values are 0
	df["total"] = df[["promoters","detractors","passives"]].sum(axis="columns")
	df["perc_pro"] = 100. * df["promoters"]/df["total"]
	df["perc_det"] = 100. * df["detractors"]/df["total"]
	df["nps"] = df["perc_pro"] - df["perc_det"]
	df["var_nps"] = df["nps"] - r.json()["periods"][0]["total"]["value"]
	df["var_color"] = df["var_nps"].apply(lambda x: {True: "seagreen", False: "orangered"}[x>=0])
	df.sort_values("nps", ascending=True, inplace=True)
	# Plot detailed NPS
	print("\trender absolute")
	df.plot.barh(
		# x is index = opinion
		y=["detractors","passives","promoters"], 
		stacked=True,
		title="Detailed NPS per top opinion",
		colormap=colors.ListedColormap(['orangered','gold','seagreen'])
	)
	plt.savefig("uc4-nps-detailed-per-top10-opinions.png")
	plt.show()
	# Plot NPS variation
	print("\trender variations")
	ax = df.plot.scatter(
		x="var_nps",
		y="nps",
		s=df["total"].values,
		c=df["var_color"].values,
		title="NPS variations per opinion"
	)
	for r in df.itertuples():
		ax.annotate(r.Index, (r.var_nps,r.nps))
	plt.savefig("uc4-nps-detailed-variation-per-top10-opinions.png")
	plt.show()
	# Save NPS per opinion of next step
	df_nps_opinion = df["nps"]

	###################################### NPS PER OPINION WITH POLARITY
	# Compute the NPS for the top 10 opinions by polarity
	print("NPS per top opinion with polarity")
	print("\tquery")
	query = {
		"type": "NPS",
		"field": "metadata.rating_nps",
		"dimensions": [
			{
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 10
			}, {
				"field": "TERMS_POLARITY",
				"group": "DISTINCT"
			}
		]
	}
	r = requests.post(
			"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
			json=query,
			auth=dictanova_auth)
	print("\t%s"%r)
	# Load in pandas
	print("\tprepare")
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df["opinion"] = df["dimensions"].apply(lambda x: x[0])
	df["polarity"] = df["dimensions"].apply(lambda x: x[1])
	df = df.pivot_table(index="opinion", columns="polarity", values="value")
	df["ref_nps_global"] = r.json()["periods"][0]["total"]["value"]
	df["var_npsg_pos"] = df["POSITIVE"] - df["ref_nps_global"]
	df["var_npsg_neg"] = df["NEGATIVE"] - df["ref_nps_global"]
	df["var_npsg_neu"] = df["NEUTRAL"] - df["ref_nps_global"]
	df["ref_nps_opinion"] = df_nps_opinion
	df["var_npsl_pos"] = df["POSITIVE"] - df["ref_nps_opinion"]
	df["var_npsl_neg"] = df["NEGATIVE"] - df["ref_nps_opinion"]
	df["var_npsl_neu"] = df["NEUTRAL"] - df["ref_nps_opinion"]
	# Plot global NPS variation per opinion and per polarity
	print("\trender variation with global NPS")
	ax = df.plot.barh(
		# x is index = opinion
		y=["var_npsg_pos","var_npsg_neg","var_npsg_neu"],
		title="Variation with global NPS for top 10 opinions and their polarity",
		colormap=colors.ListedColormap(['seagreen', 'orangered', 'darkgrey'])
	)
	ax.legend(labels=["Positive", "Negative", "Neutral"])
	plt.savefig("uc4-global-nps-variation-per-top10-opinions-with-polarity.png")
	plt.show()
	# Plot local NPS variation per opinion and per polarity
	print("\trender variation with local NPS (opinion)")
	ax = df.plot.barh(
		# x is index = opinion
		y=["var_npsl_pos","var_npsl_neg","var_npsl_neu"],
		title="Variation with local NPS for top 10 opinions and their polarity",
		colormap=colors.ListedColormap(['seagreen', 'orangered', 'darkgrey'])
	)
	ax.legend(labels=["Positive", "Negative", "Neutral"]) 
	plt.savefig("uc4-local-nps-variation-per-top10-opinions-with-polarity.png")
	plt.show()