import os
from flask import Flask, redirect, url_for, session, request, render_template_string
from dotenv import load_dotenv
import msal
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "Bobaisgreat") #secret based on team

CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}" 
REDIRECT_PATH = os.environ.get("REDIRECT_PATH")
SCOPES = ["User.Read"]  # Microsoft Graph basic profile
def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET, token_cache=cache
    )

@app.route("/")
def index():
    user = session.get("user")
    html = """
    <h1>Flask + Microsoft Entra Login</h1>
    {% if user %}
      <p>Signed in as: <b>{{ user.get('name') }}</b> ({{ user.get('preferred_username') }})</p>
      <p><a href="{{ url_for('me') }}">Call Graph /me</a></p>
      <p><a href="{{ url_for('logout') }}">Sign out</a></p>
    {% else %}
<a href="{{ url_for('login') }}" class="ms-login-btn">
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 23 23">
    <rect width="10" height="10" x="1" y="1" fill="#f25022"/>
    <rect width="10" height="10" x="12" y="1" fill="#7fba00"/>
    <rect width="10" height="10" x="1" y="12" fill="#00a4ef"/>
    <rect width="10" height="10" x="12" y="12" fill="#ffb900"/>
  </svg>
  <span>Sign in with Microsoft</span>
</a>

<style>
.ms-login-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid #ccc;
  border-radius: 6px;
  text-decoration: none;
  color: #333;
  font-family: Arial, sans-serif;
  font-size: 14px;
  background: #fff;
  transition: background 0.2s, box-shadow 0.2s;
}

.ms-login-btn:hover {
  background: #f3f3f3;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.ms-login-btn svg {
  flex-shrink: 0;
}
</style>

    {% endif %}
    """
    return render_template_string(html, user=user)

@app.route("/login")
def login():
    redirect_uri = url_for("authorized", _external=True)  
    print("Redirect URI being used:", redirect_uri)      # Having issues with return address
    flow = build_msal_app().initiate_auth_code_flow(
        SCOPES, redirect_uri=redirect_uri
    )
    session["flow"] = flow
    return redirect(flow["auth_uri"])

@app.route(REDIRECT_PATH)
def authorized():
    flow = session.get("flow")
    if not flow:
        return redirect(url_for("index"))
    try:
        result = build_msal_app().acquire_token_by_auth_code_flow(flow, request.args)
    except ValueError:
        return "Auth code flow error.", 400

    if "error" in result:
        return f"Error: {result['error']} - {result.get('error_description')}", 400

    session["user"] = result.get("id_token_claims")
    session["access_token"] = result.get("access_token")
    print("Redirect URI being used:", url_for("authorized", _external=True))
    return redirect(url_for("hello"))   

#test info
@app.route("/me")
def me():
    token = session.get("access_token")
    if not token:
        return redirect(url_for("login"))
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    return (resp.text, resp.status_code, {"Content-Type": "application/json"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri="
        + url_for("index", _external=True)
    )

@app.route("/hello")
def hello():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    html = """
    <h1>Hello, {{ user.get('name') }}!</h1>
    <p>Email: {{ user.get('preferred_username') }}</p>
    <p>Object ID: {{ user.get('oid') }}</p>
    <p><a href="{{ url_for('logout') }}">Sign out</a></p>
    """
    return render_template_string(html, user=user)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
ß