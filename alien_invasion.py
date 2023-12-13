import sys
from time import sleep # So we can pause the game for a moment when the ship is hit
import pygame

from settings import Settings
from game_stats import GameStats
from scoreboard import Scoreboard
from button import Button
from ship import Ship
from bullets import Bullet
from alien import Alien

class AlienInvasion:
	'''Overall class to manage game assets and behavior.'''

	def __init__(self):
		'''Initialize the game, and create game resources'''
		pygame.init()
		self.settings = Settings()

		# Game ran in a separate window
		self.screen = pygame.display.set_mode((self.settings.screen_width, self.settings.screen_height))

		# Full screen mode (doesn't run as well on my surface pro)
		'''self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
		self.settings.screen_width = self.screen.get_rect().width
		self.settings.screen_height = self.screen.get_rect().height'''
		
		pygame.display.set_caption("Alien Invasion")

		# Create an instance to store game statistics and create a scoreboard
		self.stats = GameStats(self)
		self.sb = Scoreboard(self)

		self.ship = Ship(self)
		self.bullets = pygame.sprite.Group()
		self.aliens = pygame.sprite.Group()

		self._create_fleet()

		# Make the play button
		self.play_button = Button(self, "Play")

	# Main Loop
	def run_game(self):
		'''Start the main loop for the game'''
		while True:
			self._check_events()
			
			if self.stats.game_active:
				self.ship.update()
				self._update_bullets()
				self._update_aliens()
			
			self._update_screen()

	def _create_fleet(self):
		'''Create the fleet of aliens'''
		# Create an alien and find the number of aliens in a row
		# Spacing between each alien is equal to one alien width
		alien = Alien(self) # This alien is only for calculation purposes and is not in the fleet
		alien_width, alien_height = alien.rect.size
		available_space_x = self.settings.screen_width - (2 * alien_width)
		number_aliens_x = available_space_x // (2 * alien_width)

		# Determine the number of rows of aliens that fit on the screen
		ship_height = self.ship.rect.height
		available_space_y = (self.settings.screen_height - (3 * alien_height) - ship_height)
		number_rows = available_space_y // (2 * alien_height)

		# Create the full fleet of aliens
		for row_number in range(number_rows):
			for alien_number in range(number_aliens_x):
				self._create_alien(alien_number, row_number) # Needs to pass in 2 parameters

	# This helper method requires and additional parameters from the newly created alien_number and row_number
	def _create_alien(self, alien_number, row_number):
		'''Create an alien and place it in a row'''
		alien = Alien(self)

		# We now get the width of an alien inside this method instead of passimg it in as an argument
		alien_width, alien_height = alien.rect.size

		# Each alien is pushed to the right one alien width and we multiply the alien width by 2 to
		# account for the space each alien takes up, including the empty space to the right and we
		# multiply this amount by the alien's position in the row
		alien.x = alien_width + (2 * alien_width * alien_number)
		alien.rect.x = alien.x
		alien.rect.y = alien.rect.height + 2 * alien.rect.height * row_number
		self.aliens.add(alien)

	def _update_aliens(self):
		'''
		Check if the fleet is at an edge, then update the positions of all aliens in the fleet
		'''
		self._check_fleet_edges()
		self.aliens.update()

		# Look for alien-ship collisions
		if pygame.sprite.spritecollideany(self.ship, self.aliens):
			self._ship_hit()

		# Look for aliens hitting the bottom of the screen
		self._check_aliens_bottom()

	def _check_events(self):
		'''Respond to keypresses and mouse events'''
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				sys.exit()
			elif event.type == pygame.KEYDOWN:
				self._check_keydown_events(event)
			elif event.type == pygame.KEYUP:
				self._check_keyup_events(event)
			elif event.type == pygame.MOUSEBUTTONDOWN:
				mouse_pos = pygame.mouse.get_pos()
				self._check_play_button(mouse_pos)

	def _check_play_button(self, mouse_pos):
		'''Start a new game when the player clicks Play'''
		button_clicked = self.play_button.rect.collidepoint(mouse_pos)
		if button_clicked and not self.stats.game_active:
			# Reset the game settings
			self.settings.initialize_dynamic_settings()
			
			# Reset the game statistics
			self.stats.reset_stats()
			self.stats.game_active = True
			self.sb.prep_score()
			self.sb.prep_level()
			self.sb.prep_ships()

			# Get rid of any remaining aliens and bullets
			self.aliens.empty()
			self.bullets.empty()

			# Create a new fleet and center the ship
			self._create_fleet()
			self.ship.center_ship()

			# Hide the mouse cursor
			pygame.mouse.set_visible(False)

	def _check_keydown_events(self, event):
		'''Respond to keypresses'''
		if event.key == pygame.K_RIGHT:
			self.ship.moving_right = True
		elif event.key == pygame.K_LEFT:
			self.ship.moving_left = True
		elif event.key == pygame.K_q:
			sys.exit()
		elif event.key == pygame.K_SPACE:
			self._fire_bullet()

	def _check_keyup_events(self, event):
		'''Respond to key releases'''
		if event.key == pygame.K_RIGHT:
			self.ship.moving_right = False
		elif event.key == pygame.K_LEFT:
			self.ship.moving_left = False

	def _check_fleet_edges(self):
		'''Respond appropriately if any aliens have reached an edge'''
		for alien in self.aliens.sprites():
			if alien.check_edges():
				self._change_fleet_direction()
				break
	
	def _change_fleet_direction(self):
		'''Drop the entire fleet and change the fleet's direction'''
		for alien in self.aliens.sprites():
			alien.rect.y += self.settings.fleet_drop_speed
		self.settings.fleet_direction *= -1

	def _check_aliens_bottom(self):
		'''Check if any aliens have reachec the bottom of the screen'''
		screen_rect = self.screen.get_rect()
		for alien in self.aliens.sprites():
			if alien.rect.bottom >= screen_rect.bottom:
				# Treat this the same as if the ship got hit
				self._ship_hit()
				break

	def _fire_bullet(self):
		'''Create a new bullet and add it to the bullets group'''
		# We check the length of the bullets group, if len(self.bullets) < the number of bullets allowed in a group
		# then we create a new bullet. If the number of allowed bullets is already fired, nothing happens when
		# the spacebar is pressed. Settings says we are allowed to fire in groups of 3
		if len(self.bullets) < self.settings.bullets_allowed:
			new_bullet =  Bullet(self)
			self.bullets.add(new_bullet)

	def _update_bullets(self):
		'''Update position of the bullets and get rid of the old bullets'''
		# Update bullet positions
		self.bullets.update()

		# Get rid of bullets that have disappeared off screen (If you don't it will cause game to slow down)
		for bullet in self.bullets.copy():
			if bullet.rect.bottom <= 0:
				self.bullets.remove(bullet)

		self._check_bullet_alien_collisions()
		'''
		The below print statement shows the amount of bullets left on the screen. It increments when fired
		and decrements when the bullets hit the top of the screen. Will keep updating as long as the 
		game is runnning. Will slow down game if left in, so it is commented out. Good debugging statement
		'''
		# print(len(self.bullets))

	def _check_bullet_alien_collisions(self):
		'''Respond to bullet-alien collisions'''
		# Remove any bullets and aliens that have collided
		collisions = pygame.sprite.groupcollide(
			self.bullets, self.aliens, True, True
		)

		if collisions:   # collisions is a dictionary
			for aliens in collisions.values():
				# Any bullet that collides with an alien becomes a key in the collisions dictionary
				# The value associated with each bullet is a list of aliens it has collided with
				self.stats.score += self.settings.alien_points * len(aliens)
			self.sb.prep_score()
			self.sb.check_high_score()

		if not self.aliens:
			# Destroy existing bullets and create new fleet
			self.bullets.empty()
			self._create_fleet()
			self.settings.increase_speed()

			# Increase level
			self.stats.level += 1
			self.sb.prep_level()

	def _ship_hit(self):
		'''Respond to the ship being hit by an alien'''

		if self.stats.ships_left > 0:
			# Decrement ships left, and update scoreboard
			self.stats.ships_left -= 1
			self.sb.prep_ships()

			# Get rid of any remaining aliens and bullets
			self.aliens.empty()
			self.bullets.empty()

			# Create a new fleet and center the ship
			self._create_fleet()
			self.ship.center_ship()

			# Pause
			sleep(0.5)
		else:
			self.stats.game_active = False
			pygame.mouse.set_visible(True)

	def _update_screen(self):
		'''Update images on the screen, and flip to the new screen'''
		self.screen.fill(self.settings.bg_color)
		self.ship.blitme()
		for bullet in self.bullets.sprites():
			bullet.draw_bullet()
		self.aliens.draw(self.screen)

		# Draw the score information
		self.sb.show_score()

		# Draw the play button if the game is inactive
		if not self.stats.game_active:
			self.play_button.draw_button()

		# Make the most recently drawn screen visible
		pygame.display.flip()

if __name__ == '__main__':
	#Make a game instance, and run the game
	ai = AlienInvasion()
	ai.run_game()