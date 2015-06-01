def _get_text(response):
    try:
        return response.text     # requests 2.7.0
    except AttributeError:
        return response.content  # requests 0.8.2
