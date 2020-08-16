#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, case
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean())
    seeking_description = db.Column(db.String(150))
    website = db.Column(db.String(150))
    show = db.relationship('Show', backref='venue')

    def __repr__():
      return f'<VenueId: {self.id}, name: {self.name}>'

class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    show = db.relationship('Show', backref='artist')

    def __repr__(self):
      return f'<ArtistID: {self.id}, name: {self.name}>'
    

class Show(db.Model):
  __tablename__ = 'shows'

  id = db.Column(db.Integer, primary_key=True)
  artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))
  venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
  start_time = db.Column(db.DateTime, nullable=False)

  def __repr__():
    return f'<ShowID: {self.id}, artistID: {self.artist_id}, venueID: {self.venue_id}, start: {self.start_time}>'

db.create_all()

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  venues = db.session.query(
    Venue.city,
    Venue.state,
    Venue.id,
    Venue.name,
    func.count(Venue.id).label('cnt')) \
    .outerjoin('show') \
    .group_by(Venue.city, Venue.state, Venue.id, Venue.name) 
  data = [{'city': venue.city,
          'state': venue.state,
          'venues':[{'id': venue.id,
                    'name': venue.name,
                    'num_upcoming_shows': venue.cnt}]} for venue in venues]
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '').strip()
  count = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).count()
  venues = db.session.query(
    Venue.id,
    Venue.name,
    func.count(Show.id).label('cnt')) \
    .outerjoin('show') \
    .group_by(Venue.id) \
    .filter(Venue.name.ilike('%' + search_term + '%')) \
    .all()
  response={
    "count": count,
    "data": [{'id': venue.id,
          'name': venue.name,
          'num_upcoming_shows': venue.cnt} for venue in venues]
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue_result = db.session.query(
    Venue.id,
    Venue.name,
    Venue.genres,
    Venue.address,
    Venue.city,
    Venue.state,
    Venue.phone,
    Venue.website,
    Venue.facebook_link,
    Venue.seeking_talent,
    Venue.seeking_description,
    Venue.image_link,
    func.count(case([(Show.start_time >= datetime.now(), 1)])).label('upcoming_shows_count'),
    func.count(case([(Show.start_time < datetime.now(), 1)])).label('past_shows_count')) \
    .outerjoin('show') \
    .group_by(Venue.id, Venue.name, Venue.genres, Venue.address, Venue.city, Venue.state, Venue.phone,
    Venue.website, Venue.facebook_link, Venue.seeking_talent, Venue.seeking_description, Venue.image_link) \
    .filter(Venue.id == venue_id) \
    .one()
  venue = dict(zip(venue_result.keys(), venue_result))
  upcoming = db.session.query(Show) \
              .join(Venue) \
              .filter(Show.venue_id == venue_id) \
              .filter(Show.start_time > datetime.now()) \
              .all()
  past = db.session.query(Show) \
          .join(Venue) \
          .filter(Show.venue_id == venue_id) \
          .filter(Show.start_time < datetime.now()) \
          .all()
  data={
    "id": venue['id'],
    "name": venue['name'],
    "genres": [genre for genre in venue['genres']],
    "address": venue['address'],
    "city": venue['city'],
    "state": venue['state'],
    "phone": venue['phone'],
    "website": venue['website'],
    "facebook_link": venue['facebook_link'],
    "seeking_talent": venue['seeking_talent'],
    "seeking_description": venue['seeking_description'],
    "image_link": venue['image_link'],
    "past_shows": [{
      "artist_id": show.id,
      "artist_name": show.name,
      "artist_image_link": show.artist_image_link,
      "start_time": show.start_time
    } for show in past],
    "upcoming_shows": [{
      "artist_id": show.id,
      "artist_name": show.name,
      "artist_image_link": show.artist_image_link,
      "start_time": show.start_time
    } for show in upcoming],
    "past_shows_count": venue['past_shows_count'],
    "upcoming_shows_count": venue['upcoming_shows_count'],
  }
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False 
  data = request.form 
  try:
    name = VenueForm().name.data
    city = VenueForm().city.data 
    state = VenueForm().state.data
    address = VenueForm().address.data
    phone = VenueForm().phone.data
    genres = ','.join(VenueForm().genres.data)
    facebook_link = VenueForm().facebook_link.data

    venue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres, facebook_link=facebook_link)
    db.session.add(venue)
    db.session.commit()
  except:
    db.session.rollback()
    error=True
    print(sys.exc_info())
  finally:
    db.session.close()
    if error:
      flash(f"An error occurred. Venue {request.form['name']} could not be listed.")
    else:
      flash(f"Venue {request.form['name']} was successfully listed!")
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    db.session.rollback()
  finally:
    db.session.close()
  return redirect(url_for('venues'))
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = Artist.query.with_entities(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '').strip()
  count = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).count()
  artists = db.session.query(
    Artist.id,
    Artist.name,
    func.count(Show.id).label('cnt')) \
    .outerjoin('show') \
    .group_by(Artist.id, Artist.name) \
    .filter(Artist.name.ilike('%' + search_term + '%')) \
    .all()
  response={
    "count": count,
    "data": [{
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": artist.cnt,
    } for artist in artists]
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist_result = db.session.query(
    Artist.id,
    Artist.name,
    Artist.genres,
    Artist.city,
    Artist.state,
    Artist.phone,
    Artist.website,
    Artist.facebook_link,
    Artist.seeking_venue,
    Artist.seeking_description,
    Artist.image_link,
    func.count(case([(Show.start_time > datetime.now(), 1)])).label('upcoming_shows_count'),
    func.count(case([(Show.start_time < datetime.now(), 1)])).label('past_shows_count')) \
    .outerjoin('show') \
    .group_by(Artist.id, Artist.name, Artist.genres, Artist.city, Artist.state, Artist.phone,
    Artist.website, Artist.facebook_link, Artist.seeking_venue, Artist.seeking_description, Artist.image_link) \
    .filter(Artist.id == artist_id) \
    .one()
  artist = dict(zip(artist_result.keys(), artist_result))
  upcoming = db.session.query(Show) \
              .join(Artist) \
              .filter(Show.venue_id == venue_id) \
              .filter(Show.start_time > datetime.now()) \
              .all()
  past = db.session.query(Show) \
          .join(Artist) \
          .filter(Show.venue_id == venue_id) \
          .filter(Show.start_time < datetime.now()) \
          .all()
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id
  data={
    "id": artist['id'],
    "name": artist['name'],
    "genres": [genre for genre in artist['genres']],
    "city": artist['city'],
    "state": artist['state'],
    "phone": artist['phone'],
    "website": artist['website'],
    "facebook_link": artist['facebook_link'],
    "seeking_venue": artist['seeking_venue'],
    "seeking_description": artist['seeking_description'],
    "image_link": artist['image_link'],
    "past_shows": [{
      "venue_id": show.id,
      "venue_name": show.name,
      "venue_image_link": show.image_link,
      "start_time": show.start_time
    } for show in past],
    "upcoming_shows": [{
      "venue_id": show.id,
      "venue_name": show.name,
      "venue_image_link": show.image_link,
      "start_time": show.start_time
    } for show in upcoming],
    "past_shows_count": artist['past_shows_count'],
    "upcoming_shows_count": artist['upcoming_shows_count'],
  }
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  artist = request.form.to_dict()
  try:
    Artist.query.filter_by(id=artist_id).update(artist)
    Artist.query.filter_by(id=artist_id).update(dict(genres=request.form.getlist('genres')))
    db.session.commit()
    flash(f'Artist {artist.name} was successfully listed!')
  except:
    db.session.rollback()
    flash(f'Artist {artist.name} was not listed, please try again!')
  finally:
    db.session.close()
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.filter_by(id=venue_id).all()[0]
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  venue = request.form.to_dict()
  try:
    Venue.query.filter_by(id=venue_id).update(venue)
    Venue.query.filter_by(id=venue_id).update(dict(genres=request.form.getlist('genres')))
    db.session.commit()
    flash(f'Artist {venue.name} was successfully listed!')
  except:
    db.session.rollback()
    flash(f'Artist {venue.name} was not listed, please try again!')
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  artist = request.form.to_dict()
  print(artist)
  try:
    name = artist['name']
    city = artist['city']
    state = artist['state']
    phone = artist['phone']
    genres = request.form.getlist('genres')
    facebook_link = artist['facebook_link']

    artist = Artist(name = name, city = city, state = state, phone = phone, genres = genres, facebook_link = facebook_link)
    db.session.add(artist)
    db.session.commit()
    flash('Artist '+ artist['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('Artist ' + artist['name'] + ' was not listed, please try again!')
  finally:
    db.session.close()
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = Show.query.join(Artist).all()

  data = [{"venue_id": show.show_id,
          "venue_name": show.show_name,
          "artist_id": show.artist_id,
          "artist_name": show.artist_name,
          "artist_image_link": show.artist_image_link,
          "start_time": show.show_start_time} for show in shows]
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    show = request.form.to_dict()
    start_time_format = datetime.strptime(show['start_time'], '%Y-%m-%d %H:%M:%S')
    new_show = Show(venue_id = show['venue_id'], artist_id = show['artist_id'], start_time = start_time_format)
    db.session.add(new_show)
    db.session.commit()
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
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
