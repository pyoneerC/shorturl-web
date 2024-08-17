from flask import Flask, render_template, request, redirect, url_for, flash
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey'

url_map = {}

def generate_short_code(length=6):
    """Generate a random string of fixed length."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

@app.route('/', methods=['GET', 'POST'])
def shorten_url():
    if request.method == 'POST':
        original_url = request.form['url']
        short_code = generate_short_code()

        url_map[short_code] = {
            'original_url': original_url,
            'created_at': datetime.now(),
            'last_updated_at': datetime.now(),
            'expiration_date': datetime.now() + timedelta(days=30),  # Example: 30-day expiration
            'access_count': 0
        }

        flash(f'URL shortened: {request.host_url}{short_code}', 'success')

        return redirect(url_for('shorten_url'))

    return render_template('index.html')

@app.route('/<short_code>')
def redirect_to_url(short_code):
    url_data = url_map.get(short_code)
    if url_data:
        url_data['access_count'] += 1
        url_data['last_updated_at'] = datetime.now()

        return redirect(url_data['original_url'])
    else:
        flash('Invalid short URL', 'danger')
        return redirect(url_for('shorten_url'))

@app.route('/shorten/<short_code>')
def url_info(short_code):
    url_data = url_map.get(short_code)
    if url_data:
        return render_template('url_info.html', data={
            'short_code': short_code,
            'original_url': url_data['original_url'],
            'created_at': url_data['created_at'],
            'last_updated_at': url_data['last_updated_at'],
            'expiration_date': url_data['expiration_date'],
            'access_count': url_data['access_count']
        })
    else:
        flash('Invalid short URL', 'danger')
        return redirect(url_for('shorten_url'))

if __name__ == '__main__':
    app.run(debug=True)
