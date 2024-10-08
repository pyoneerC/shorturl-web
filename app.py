from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'


@app.route('/', methods=['GET', 'POST'])
def shorten_url():
    if request.method == 'POST':
        original_url = request.form['url']

        try:
            response = requests.post(
                "https://url-shortener-backend-xzs2.onrender.com/shorten/",
                params={"url": original_url}
            )
            response.raise_for_status()
            shortened_url = response.json().get('short_code')

            if shortened_url:
                flash(f'Shortened URL: {request.host_url}{shortened_url}', 'success')
            else:
                flash('Failed to shorten the URL. Please try again.', 'danger')
        except requests.RequestException as e:
            flash(f'Error: {e}', 'danger')

        return redirect(url_for('shorten_url'))

    return render_template('index.html')


@app.route('/<short_code>')
def redirect_to_url(short_code):
    try:
        response = requests.get(f"https://url-shortener-backend-xzs2.onrender.com/shorten/{short_code}")
        response.raise_for_status()
        original_url = response.json().get('original_url')
        return redirect(original_url)
    except requests.RequestException:
        flash('Invalid short URL', 'danger')
        return redirect(url_for('shorten_url'))

access_count = 0

@app.route('/shorten/<short_code>')
def url_info(short_code):
    try:
        response = requests.get(f"https://url-shortener-backend-xzs2.onrender.com/shorten/{short_code}")
        response.raise_for_status()
        url_data = response.json()
        global access_count
        access_count += 1

        return render_template('url_info.html', data=url_data, access_count=access_count)
    except requests.RequestException:
        flash('Invalid short URL', 'danger')
        return redirect(url_for('shorten_url'))

@app.route('/delete/<short_code>')
def delete_url(short_code):
    try:
        response = requests.delete(f"https://url-shortener-backend-xzs2.onrender.com/shorten/{short_code}")
        response.raise_for_status()
        flash('URL deleted successfully', 'success')
    except requests.RequestException:
        flash('Failed to delete the URL', 'danger')

    return redirect(url_for('shorten_url'))


@app.route('/update/<short_code>', methods=['POST'])
def update_url(short_code):
    data = request.get_json()
    new_url = data.get('url')

    if not new_url:
        return jsonify({"message": "No URL provided"}), 400

    try:
        response = requests.put(
            f"https://url-shortener-backend-xzs2.onrender.com/shorten/",
            params={"short_code": short_code, "url": new_url}
        )
        response.raise_for_status()
        return jsonify({"message": "URL updated successfully"}), 200
    except requests.RequestException:
        return jsonify({"message": "Failed to update the URL"}), 400




if __name__ == '__main__':
    app.run(debug=True)
