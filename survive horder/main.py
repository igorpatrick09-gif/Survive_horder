import pgzrun
import random
import math
from pygame import Rect  

# ==============================================================================
# CONFIGURAÇÕES DE TELA E ESTADOS DO JOGO
# ==============================================================================
WIDTH = 800
HEIGHT = 480
GROUND_Y = 430  

game_state = "MENU"  
audio_enabled = True
score = 0
high_score = 0
current_stage = 1   

spawn_timer = 0
SPAWN_COOLDOWN = 100  
player_death_timer = 0  

# Plataformas flutuantes
platforms = [
    Rect((150, 300), (180, 20)),
    Rect((470, 300), (180, 20)),
    Rect((300, 180), (200, 20))
]

# ==============================================================================
# CONFIGURAÇÃO DOS BOTÕES DA INTERFACE
# ==============================================================================
BUTTON_WIDTH = 250  
BUTTON_HEIGHT = 50
BUTTON_X = (WIDTH // 2) - (BUTTON_WIDTH // 2)

btn_start_rect = Rect((BUTTON_X, 180), (BUTTON_WIDTH, BUTTON_HEIGHT))
btn_sound_rect = Rect((BUTTON_X, 250), (BUTTON_WIDTH, BUTTON_HEIGHT))
btn_exit_rect = Rect((BUTTON_X, 320), (BUTTON_WIDTH, BUTTON_HEIGHT))
btn_next_stage_rect = Rect((BUTTON_X, 260), (BUTTON_WIDTH, BUTTON_HEIGHT))
btn_restart_rect = Rect((BUTTON_X, 280), (BUTTON_WIDTH, BUTTON_HEIGHT))
btn_gameover_menu_rect = Rect((BUTTON_X, 350), (BUTTON_WIDTH, BUTTON_HEIGHT))

# ==============================================================================
# CLASSES DE SISTEMA
# ==============================================================================

class MovementSystem:
    """Gerencia física, gravidade, limites e colisões com plataformas."""
    def __init__(self, gravity=0.6):
        self.gravity = gravity

    def apply_gravity(self, entity):
        entity.velocity_y += self.gravity
        entity.actor.y += entity.velocity_y

    def handle_platform_collisions(self, entity, platforms_list):
        entity.is_on_ground = False
        
        if entity.velocity_y > 0:
            for platform in platforms_list:
                if entity.actor.colliderect(platform):
                    if (entity.actor.bottom - entity.velocity_y) <= platform.top + 15:
                        entity.actor.bottom = platform.top
                        entity.velocity_y = 0
                        entity.is_on_ground = True
                        return

        if entity.actor.bottom >= GROUND_Y:
            entity.actor.bottom = GROUND_Y
            entity.velocity_y = 0
            entity.is_on_ground = True


class AnimationSystem:
    """Gerencia a lógica de troca de sprites baseada na direção."""
    def __init__(self, frame_duration=10):
        self.frame_duration = frame_duration

    def update_animation(self, entity, base_name, total_frames=2):
        entity.animation_timer += 1
        if entity.animation_timer >= self.frame_duration:
            entity.animation_frame = (entity.animation_frame % total_frames) + 1
            entity.animation_timer = 0
        
        suffix = "" if entity.facing_right else "_left"
        entity.actor.image = f"{base_name}{entity.animation_frame}{suffix}"


# Instâncias globais dos sistemas
movement_system = MovementSystem()
animation_system = AnimationSystem()

# ==============================================================================
# CLASSES DE ENTIDADE (Jogador e Inimigo)
# ==============================================================================

class Player:
    def __init__(self, x, bottom_y):
        self.actor = Actor("mc_idle")
        self.actor.x = x
        self.actor.bottom = bottom_y
        
        self.velocity_x = 5
        self.velocity_y = 0
        self.is_on_ground = False
        
        self.is_attacking = False
        self.attack_cooldown = 0
        
        self.animation_frame = 1
        self.animation_timer = 0
        self.facing_right = True  
        
        self.lives = 3
        self.invulnerable_timer = 0  

    def handle_input(self, keyboard):
        is_moving = False

        if keyboard.left and self.actor.left > 0:
            self.actor.x -= self.velocity_x
            self.facing_right = False  
            is_moving = True
        if keyboard.right and self.actor.right < WIDTH:
            self.actor.x += self.velocity_x
            self.facing_right = True   
            is_moving = True

        if is_moving and self.is_on_ground and not self.is_attacking:
            animation_system.update_animation(self, "mc_walk", 2)
        elif self.is_on_ground and not self.is_attacking:
            self.actor.image = "mc_idle" if self.facing_right else "mc_idle_left"

        if keyboard.up and self.is_on_ground and not self.is_attacking:
            self.velocity_y = -12.5  
            self.is_on_ground = False

        if keyboard.k and self.attack_cooldown == 0:
            self.is_attacking = True
            self.actor.image = "mc_kick" if self.facing_right else "mc_kick_left"
            self.attack_cooldown = 18
            if audio_enabled:
                try: sounds.punch_kick.play()
                except (NameError, AttributeError, Exception): pass

    def update(self):
        movement_system.apply_gravity(self)
        movement_system.handle_platform_collisions(self, platforms)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown == 0:
                self.is_attacking = False

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1

    def draw(self):
        if game_state == "DYING" or self.invulnerable_timer % 4 < 2:
            self.actor.draw()


class Enemy:
    def __init__(self, enemy_type, platform_assigned=None):
        self.enemy_type = enemy_type
        self.actor = Actor(f"enemy_{enemy_type}_walk1")
        self.platform_assigned = platform_assigned  
        
        self.animation_frame = 1
        self.animation_timer = 0
        self.facing_right = True  
        
        speed_multiplier = 1.0 + (current_stage - 1) * 0.4
        base_speed = random.uniform(1.5, 2.8) * speed_multiplier

        if self.platform_assigned:
            self.actor.x = platform_assigned.centerx
            self.actor.bottom = platform_assigned.top
            self.velocity_x = base_speed if random.choice([True, False]) else -base_speed
        else:
            self.actor.x = WIDTH + 60
            self.actor.bottom = GROUND_Y
            self.velocity_x = -base_speed  
            
        self.is_dead = False
        self.death_timer = 0

    def update_ai(self):
        if not self.is_dead:
            self.actor.x += self.velocity_x
            
            if self.velocity_x > 0:
                self.facing_right = True   
            else:
                self.facing_right = False  
            
            animation_system.update_animation(self, f"enemy_{self.enemy_type}_walk", 2)
            
            if self.platform_assigned:
                if self.actor.left <= self.platform_assigned.left:
                    self.velocity_x = abs(self.velocity_x)
                    self.actor.left = self.platform_assigned.left
                elif self.actor.right >= self.platform_assigned.right:
                    self.velocity_x = -abs(self.velocity_x)
                    self.actor.right = self.platform_assigned.right
        else:
            suffix = "" if self.facing_right else "_left"
            self.actor.image = f"enemy_{self.enemy_type}_dead{suffix}"
            self.actor.y += 5
            self.death_timer -= 1

    def draw(self):
        self.actor.draw()

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
player = Player(100, GROUND_Y)
enemies = []

def spawn_initial_platform_enemies():
    enemies.clear()
    enemy_types = ["robot", "soldier", "zombie"]
    for platform in platforms:
        enemies.append(Enemy(random.choice(enemy_types), platform_assigned=platform))

spawn_initial_platform_enemies()

# ==============================================================================
# GERENCIAMENTO DE ÁUDIO E FUNÇÕES AUXILIARES DA UI
# ==============================================================================

def manage_music():
    if audio_enabled and game_state == "PLAYING":
        try: sounds.bgmusic.play(-1)
        except (NameError, AttributeError, Exception): pass
    else:
        try: sounds.bgmusic.stop()
        except (NameError, AttributeError, Exception): pass

def draw_menu_button(button_rect, text, color):
    screen.draw.filled_rect(button_rect, color)
    screen.draw.rect(button_rect, (255, 255, 255))
    text_x = button_rect.x + (button_rect.width // 2)
    text_y = button_rect.y + (button_rect.height // 2)
    screen.draw.text(text, center=(text_x, text_y), fontsize=20, color="white")

# ==============================================================================
# LOOPS PRINCIPAIS DO MOTOR (DESENHO E ATUALIZAÇÃO)
# ==============================================================================

def draw():
    if current_stage == 1:
        screen.fill((135, 206, 235))
    elif current_stage == 2:
        screen.fill((244, 128, 36))
    else:
        screen.fill((20, 24, 82))

    if game_state == "MENU":
        screen.draw.text("SURVIVE HORDER", center=(400, 90), fontsize=55, color="white", shadow=(2, 2))
        screen.draw.text(f"HIGH SCORE: {high_score}", center=(400, 140), fontsize=25, color="yellow")
        draw_menu_button(btn_start_rect, "Iniciar Jogo", (50, 150, 50))
        sound_text = "Som: LIGADO" if audio_enabled else "Som: DESLIGADO"
        sound_color = (70, 70, 150) if audio_enabled else (150, 70, 70)
        draw_menu_button(btn_sound_rect, sound_text, sound_color)
        draw_menu_button(btn_exit_rect, "Sair", (100, 100, 100))

    elif game_state in ["PLAYING", "DYING"]:
        screen.draw.filled_rect(Rect((0, GROUND_Y), (WIDTH, HEIGHT - GROUND_Y)), (50, 180, 50))
        
        for platform in platforms:
            screen.draw.filled_rect(platform, (90, 60, 40))
            screen.draw.rect(platform, (120, 90, 70))

        screen.draw.text(f"SCORE: {score}", topleft=(20, 20), fontsize=32, color="white")
        screen.draw.text(f"FASE: {current_stage}", center=(WIDTH // 2, 30), fontsize=32, color="white")

        if game_state == "PLAYING":
            for i in range(player.lives):
                screen.draw.filled_circle((WIDTH - 40 - i * 35, 30), 12, (255, 0, 0))

        player.draw()

        for enemy in enemies:
            enemy.draw()

    elif game_state == "STAGE_CLEAR":
        screen.draw.filled_rect(Rect((0, GROUND_Y), (WIDTH, HEIGHT - GROUND_Y)), (50, 180, 50))
        for platform in platforms:
            screen.draw.filled_rect(platform, (90, 60, 40))
        player.draw()
        for enemy in enemies:
            enemy.draw()

        screen.draw.filled_rect(Rect((0, 0), (WIDTH, HEIGHT)), (0, 0, 0))
        screen.draw.text(f"FASE {current_stage} CONCLUÍDA!", center=(400, 150), fontsize=45, color="yellow")

        if current_stage < 3:
            draw_menu_button(btn_next_stage_rect, "Próxima Fase", (50, 150, 50))
        else:
            screen.draw.text("VOCÊ ZEROU O JOGO!", center=(400, 220), fontsize=28, color="white")
            draw_menu_button(btn_next_stage_rect, "Menu Principal", (70, 70, 150))

    elif game_state == "GAME_OVER":
        screen.fill((20, 20, 20))
        screen.draw.text("GAME OVER", center=(WIDTH // 2, 90), fontsize=70, color="red")
        screen.draw.text(f"SCORE FINAL: {score}", center=(WIDTH // 2, 170), fontsize=35, color="white")
        screen.draw.text(f"RECORDE: {high_score}", center=(WIDTH // 2, 210), fontsize=30, color="yellow")
        draw_menu_button(btn_restart_rect, "JOGAR NOVAMENTE", (50, 150, 50))
        draw_menu_button(btn_gameover_menu_rect, "MENU PRINCIPAL", (70, 70, 150))


def update():
    global game_state, spawn_timer, score, high_score, current_stage, player_death_timer
    
    if game_state == "PLAYING":
        player.handle_input(keyboard)
        player.update()
        
        if score >= 50 and current_stage == 1:
            game_state = "STAGE_CLEAR"
            if audio_enabled:
                try: sounds.congratulations.play()
                except (NameError, AttributeError, Exception): pass
                
        elif score >= 120 and current_stage == 2:
            game_state = "STAGE_CLEAR"
            if audio_enabled:
                try: sounds.congratulations.play()
                except (NameError, AttributeError, Exception): pass

        elif score >= 200 and current_stage == 3:
            game_state = "STAGE_CLEAR"
            if score > high_score:
                high_score = score
            try: 
                sounds.bgmusic.stop()
                if audio_enabled:
                    sounds.congratulations.play()
            except (NameError, AttributeError, Exception): pass
        
        spawn_timer += 1
        if spawn_timer >= SPAWN_COOLDOWN:
            spawn_timer = 0
            enemy_types = ["robot", "soldier", "zombie"]
            enemies.append(Enemy(random.choice(enemy_types), platform_assigned=None))
        
        for enemy in list(enemies):
            enemy.update_ai()
            
            if enemy.is_dead and enemy.death_timer <= 0:
                enemies.remove(enemy)
                continue
            
            if not enemy.platform_assigned and enemy.actor.right < 0:
                enemies.remove(enemy)
                score += 5
                continue
                
            if not enemy.is_dead:
                is_colliding = player.actor.colliderect(enemy.actor)
                
                if is_colliding:
                    if player.is_attacking:
                        if (player.facing_right and enemy.actor.x >= player.actor.x) or (not player.facing_right and enemy.actor.x <= player.actor.x):
                            enemy.is_dead = True
                            enemy.death_timer = 25
                            score += 10
                            if audio_enabled:
                                try: sounds.hit.play()
                                except (NameError, AttributeError, Exception): pass
                    else:
                        if player.invulnerable_timer == 0:
                            player.lives -= 1
                            player.invulnerable_timer = 60
                            
                            if player.lives <= 0:
                                if score > high_score:
                                    high_score = score
                                
                                game_state = "DYING"
                                player.actor.image = "mc_dead" if player.facing_right else "mc_dead_left"
                                player.velocity_y = -10  
                                player_death_timer = 50   
                                
                                try:
                                    sounds.bgmusic.stop()
                                    if audio_enabled:
                                        sounds.gameover.play()
                                except (NameError, AttributeError, Exception): pass

    elif game_state == "DYING":
        player.velocity_y += 0.6  
        player.actor.y += player.velocity_y
        player.actor.x -= 2  
        
        for enemy in enemies:
            enemy.update_ai()

        player_death_timer -= 1
        if player_death_timer <= 0:
            game_state = "GAME_OVER"


def on_mouse_down(pos):
    global game_state, audio_enabled, current_stage, enemies, score
    
    if game_state == "MENU":
        if btn_start_rect.collidepoint(pos):
            game_state = "PLAYING"
            manage_music()
        elif btn_sound_rect.collidepoint(pos):
            audio_enabled = not audio_enabled
            manage_music()
        elif btn_exit_rect.collidepoint(pos):
            quit()

    elif game_state == "STAGE_CLEAR":
        if btn_next_stage_rect.collidepoint(pos):
            if current_stage < 3:
                current_stage += 1
                player.lives = 3  
                spawn_initial_platform_enemies()  
                game_state = "PLAYING"
            else:
                game_state = "MENU"
                manage_music()
                spawn_initial_platform_enemies()
                score = 0
                current_stage = 1
                player.lives = 3
                player.actor.x = 100
                player.actor.bottom = GROUND_Y

    elif game_state == "GAME_OVER":
        if btn_restart_rect.collidepoint(pos):
            spawn_initial_platform_enemies()  
            score = 0
            current_stage = 1
            player.lives = 3
            player.actor.x = 100
            player.actor.bottom = GROUND_Y
            game_state = "PLAYING"
            manage_music()
        elif btn_gameover_menu_rect.collidepoint(pos):
            spawn_initial_platform_enemies()
            score = 0
            current_stage = 1
            player.lives = 3
            player.actor.x = 100
            player.actor.bottom = GROUND_Y
            game_state = "MENU"
            manage_music()

pgzrun.go()