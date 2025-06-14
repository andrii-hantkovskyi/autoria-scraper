def get_user_secure_data(soup):
    script = soup.find_all("script", class_=lambda c: c and c.startswith("js-user-secure-"))[0]
    return script.get("data-hash"), script.get("data-expires") if script else None
