# dictanova-demo-python

Dictanova API is a full-stack semantic API to process customer feedbacks. You can learn 
more about it [online at dictanova.com](https://www.dictanova.com)
The technical documentation is available [at docs.dictanova.io](https://docs.dictanova.io)

This repository describes various use cases of the API.

## Setup for dictanova/demo

You need some dependencies to run those scripts:
* pandas >= 0.23
* requests
* auth0-python == 3.3.0
* DateTime == 4.2
* wordcloud == 1.4.1

To run the demo scripts, you need to create a file named `credentials` under the directory
`dictanova/demo` that will contain one line with your credential id and secret separated
by a semi colon:

    my_client_id;my_very_secret_client_secret

Read [the documentation](https://docs.dictanova.io/docs/request-your-token) to learn more 
about getting credentials.

## Demo Product Reviews

The demo Product Reviews is available in the directory `dictanova/demo/product-reviews/`
as a collection of scripts:
* `demo-product-reviews-uc1.py`: Top negative opinions of reviews from 2016 that do not 
recommand a product from a specific subcategory
* `demo-product-reviews-uc2.py`: Measure the impact of the price on the satisfaction score
per product subcategory
* `demo-product-reviews-uc3.py`: Compute the top brands in satisfaction regarding a
particular criteria in a specific subcategory
* `demo-product-reviews-uc4.py`: Generate a Llosa matrix
