#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import sys
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:xyz@localhost:5432/fyyur'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Show(db.Model):
  __tablename__ = 'Show'
  id = db.Column(db.Integer, primary_key=True)
  time = db.Column(db.DateTime, nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)

class Venue(db.Model):
    __tablename__ = 'Venue'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String()))
    address = db.Column(db.String(120))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    show_id = db.relationship('Show', backref="venue", lazy=True)

class Artist(db.Model):
    __tablename__ = 'Artist'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    show_id = db.relationship('Show', backref="artist", lazy=True)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#----------------------------------------------------------------------------#
#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  venue_locs = Venue.query.distinct(Venue.city, Venue.state).all()
  data = []
  for venue_loc in venue_locs:
    temp = []
    venues = Venue.query.filter_by(state=venue_loc.state).filter_by(city=venue_loc.city).all()
    for venue in venues:
      temp.append({
        "id": venue.id,
        "name": venue.name, 
        "num_upcoming_shows": len(Show.query.filter_by(venue_id=venue.id).filter(Show.time>datetime.now()).all())
      })
    data.append({
      "city": venue_loc.city,
      "state": venue_loc.state, 
      "venues":temp
    })
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
  result = {}
  temp = []
  for venue in venues:
    temp.append({
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": len(Show.query.filter_by(venue_id=venue.id).filter(Show.time>datetime.now()).all())
    })
  result["count"] = len(venues)
  result["data"] =  temp
  return render_template('pages/search_venues.html', results=result, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  past_shows = []
  for show in Show.query.filter_by(venue_id=venue_id).filter(Show.time<datetime.now()).all():
    artist = Artist.query.get(show.artist_id)
    past_shows.append({
      "artist_id": artist.id,
      "artist_name": artist.name,
      "artist_image_link": artist.image_link,
      "start_time": show.time.strftime("%m/%d/%Y")
    })

  upcoming_shows = []
  for show in Show.query.filter_by(venue_id=venue_id).filter(Show.time>datetime.now()).all():
    artist = Artist.query.get(show.artist_id)
    upcoming_shows.append({
      "artist_id": artist.id,
      "artist_name": artist.name,
      "artist_image_link": artist.image_link,
      "start_time": show.time.strftime("%m/%d/%Y")
    })

  venue = Venue.query.get(venue_id)
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "image_link": venue.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }
  if venue.seeking_talent:
    data["seeking_description"]= venue.seeking_description

  return render_template('pages/show_venue.html', venue=data)

#  ----------------------------------------------------------------
#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
      name = request.form['name']
      address = request.form['address']
      city = request.form['city']
      state = request.form['state']
      phone = request.form['phone']
      genres = request.form['genres']
      image_link = request.form['image_link']
      facebook_link = request.form['facebook_link']
      seeking_talent = True if 'seeking_talent' in request.form else False 
      seeking_description = request.form['seeking_description']
      venue = Venue(name=name, city=city, state=state, address=address, genres=genres, phone=phone, image_link=image_link, facebook_link=facebook_link, seeking_talent=seeking_talent, seeking_description=seeking_description)
      db.session.add(venue)
      db.session.commit()
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except:
      db.session.rollback()
      flash('An error occurred. Venue ' + venue.name + ' could not be listed.')
      print(sys.exc_info())
  finally:
      db.session.close()
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>/delete', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    return redirect(url_for('venues'))

#  ----------------------------------------------------------------
#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()
  data = []
  for artist in artists:
    data.append({
      "id": artist.id,
      "name": artist.name,
    })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
  result = {}
  temp = []
  for artist in artists:
    temp.append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": len(Show.query.filter_by(artist_id=artist.id).filter(Show.time>datetime.now()).all())
    })
  result["count"] = len(artists)
  result["data"] =  temp

  return render_template('pages/search_artists.html', results=result, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  past_shows = []
  for show in Show.query.filter_by(artist_id=artist_id).filter(Show.time<datetime.now()).all():
    venue = Venue.query.get(show.venue_id)
    past_shows.append({
      "venue_id": venue.id,
      "venue_name": venue.name,
      "venue_image_link": venue.image_link,
      "start_time": show.time.strftime("%m/%d/%Y")
    })

  upcoming_shows = []
  for show in Show.query.filter_by(artist_id=artist_id).filter(Show.time>datetime.now()).all():
    venue = Venue.query.get(show.venue_id)
    upcoming_shows.append({
      "venue_id": venue.id,
      "venue_name": venue.name,
      "venue_image_link": venue.image_link,
      "start_time": show.time.strftime("%m/%d/%Y")
    })

  artist = Artist.query.get(artist_id)
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "image_link": artist.image_link,
    "seeking_description": artist.seeking_description,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }
  return render_template('pages/show_artist.html', artist=data)

#  ----------------------------------------------------------------
#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }

  form = ArtistForm()
  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.genres.data = artist.genres
  form.facebook_link.data = artist.facebook_link
  form.image_link.data = artist.image_link
  form.website_link.data = artist.website
  form.seeking_venue.data = artist.seeking_venue
  form.seeking_description.data = artist.seeking_description
  return render_template('forms/edit_artist.html', form=form, artist=data)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  artist = Artist.query.get(artist_id)
  try: 
    artist.name = request.form['name']
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.genres = request.form.getlist('genres')
    artist.image_link = request.form['image_link']
    artist.facebook_link = request.form['facebook_link']
    artist.website = request.form['website_link']
    artist.seeking_venue = True if 'seeking_venue' in request.form else False 
    artist.seeking_description = request.form['seeking_description']
    db.session.commit()
  except: 
    db.session.rollback()
    print(sys.exc_info())
  finally: 
    db.session.close()
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "city": venue.city,
    "address": venue.address,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }

  form = ArtistForm()
  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.phone.data = venue.phone
  form.genres.data = venue.genres
  form.facebook_link.data = venue.facebook_link
  form.image_link.data = venue.image_link
  form.website_link.data = venue.website,
  form.seeking_talent.data = venue.seeking_talent
  form.seeking_description.data = venue.seeking_description
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  venue = Venue.query.get(venue_id)
  try: 
    venue.name = request.form['name']
    venue.city = request.form['city']
    venue.state = request.form['state']
    venue.phone = request.form['phone']
    venue.genres = request.form.getlist('genres')
    venue.image_link = request.form['image_link']
    venue.facebook_link = request.form['facebook_link']
    venue.website = request.form['website_link']
    venue.seeking_venue = True if 'seeking_venue' in request.form else False 
    venue.seeking_description = request.form['seeking_description']
    db.session.commit()
  except: 
    db.session.rollback()
    print(sys.exc_info())
  finally: 
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  ----------------------------------------------------------------
#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
      name = request.form['name']
      city = request.form['city']
      state = request.form['state']
      phone = request.form['phone']
      genres = request.form['genres']
      image_link = request.form['image_link']
      facebook_link = request.form['facebook_link']
      seeking_venue = True if 'seeking_venue' in request.form else False 
      seeking_description = request.form['seeking_description']
      artist = Artist(name=name, city=city, state=state, genres=genres, phone=phone, image_link=image_link, facebook_link=facebook_link, seeking_venue=seeking_venue, seeking_description=seeking_description)
      db.session.add(artist)
      db.session.commit()
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
      db.session.rollback()
      flash('An error occurred. Venue ' + artist.name + ' could not be listed.')
      print(sys.exc_info())
  finally:
      db.session.close()
  return render_template('pages/home.html')

#  ----------------------------------------------------------------
#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  shows = Show.query.join(Artist).join(Venue).all()
  for show in shows:
    data.append({
      "venue_id": show.venue_id,
      "venue_name": show.venue.name,
      "artist_id": show.artist_id,
      "artist_name": show.artist.name, 
      "artist_image_link": show.artist.image_link,
      "start_time": show.time.strftime("%m/%d/%Y")
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    time = format_datetime(request.form['start_time'])
    show = Show(artist_id=artist_id, venue_id=venue_id, time=time)
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except:
      db.session.rollback()
      flash('An error occurred. Show could not be listed.')
      print(sys.exc_info())
  finally:
      db.session.close()
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
