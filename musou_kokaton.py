import math
import os
import random
import sys
import time
import pygame as pg


WIDTH, HEIGHT = 1000, 600  # ゲームウィンドウの幅，高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct:pg.Rect) -> tuple[bool, bool]:
    """
    Rectの画面内外判定用の関数
    引数：こうかとんRect，または，爆弾Rect，またはビームRect
    戻り値：横方向判定結果，縦方向判定結果（True：画面内／False：画面外）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:  # 横方向のはみ出し判定
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, score):
        """
        押下キーに応じてこうかとんを移動させる
        スコアが100より大きいとき，右Shift押下で500フレームの間こうかとんが無敵状態になる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        引数3 score:Scoreオブジェクト
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.sum_mv = sum_mv
        key_lst = pg.key.get_pressed()
              
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if key_lst[pg.K_LSHIFT]:   #左シフトキーが押されたら
            self.rect.move_ip(2*self.speed*sum_mv[0], 2*self.speed*sum_mv[1])  #コウカトンの速度を2倍    
            if check_bound(self.rect) != (True, True):
                self.rect.move_ip(2*-self.speed*sum_mv[0], 2*-self.speed*sum_mv[1])

        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if key_lst[pg.K_RSHIFT] and score.value >= 100:
            score.value -= 100  # スコアを100消費
            self.state = "hyper"
            self.hyper_life = 500  # 発動時間
        if self.state == "hyper":   # 無敵状態のとき
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"
        screen.blit(self.image, self.rect)

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height/2
        self.speed = 6
        self.state="active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0 : float = 0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = angle0 + math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    ビームの同時発射に関するクラス
    """
    def __init__(self, bird : Bird, num : int):
        self.bird = bird
        self.num = num
    
    def gen_beams(self):
        beams = []
        for angle in range(-50, +51, 100//(self.num-1)):
            beam = Beam(self.bird, angle)
            beams.append(beam)
        return beams


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Gravity(pg.sprite.Sprite):
    def __init__(self, life : int):
        super().__init__()
        self.life = life
        self.image = pg.Surface((WIDTH, HEIGHT))
        color = (0, 0, 0)
        pg.draw.rect(self.image, color, (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()

class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス    
    """
    def __init__(self, bird : Bird, life : int):
        super().__init__()
        self.life = life
        x, y = 20, bird.rect.height*2
        self.image = pg.Surface((x, y))
        color = (0, 0, 255)
        pg.draw.rect(self.image, color, (0, 0, x, y))
        self.vx, self.vy = bird.dire
        self.angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(self.image, self.angle, 1.0)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*bird.dire[1]
        self.rect.centerx = bird.rect.centerx+bird.rect.width*bird.dire[0]

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()

class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

#empに関するクラス
class EMP():
    def __init__(self,emys: pg.sprite.Group ,bombs: pg.sprite.Group, screen : pg.Surface):
        for emy in emys:
            emy.interval = math.inf
            emy.image=pg.transform.laplacian(emy.image)
            emy.image.set_colorkey((0,0,0))
        for bomb in bombs:
            bomb.speed/=2
            bomb.state="inactive"
        
        
class color():
    def __init__(self):
        self.image=pg.Surface((1000, 600))
        pg.draw.rect(self.image,(255, 255, 255),(0, 0), )


class Enemy2(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.tmr = 0
        self.life = 30
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/alien1.png"), 0, 1.5)
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH/2, 0)
        self.vx = random.randint(2, 4)
        self.vy = +1
        self.bound_x = WIDTH//12
        self.bound_y = HEIGHT//6
        self.state = "down"
    
    def update(self, bullets : pg.sprite.Group, bird : Bird):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.tmr % 500 == 100 :
            self.n_way(12, random.randint(4, 7), bullets, bird)
        if self.tmr % 50 == 25:
            self.n_way(1, 6.0, bullets, bird)
        if self.tmr % 150 == 35:
            self.predict(16, bullets, bird)
        if self.tmr % 15 == 14:
            bullets.add(Bullet(5, random.randint(0, 359), self))
        if self.state != "down":
            self.tmr += 1
        if self.rect.centery > self.bound_y:
            self.vy = 0
            self.state = "move"
        if self.state == "move":
            self.rect.move_ip(self.vx, 0)
        if self.rect.left < self.bound_x or WIDTH-self.bound_x < self.rect.right:
            self.vx *= -1
            self.rect.move_ip(self.vx, 0)
        self.rect.centery += self.vy

    def PlusMin(self, a, b):
        if a < 0 and b < 0:
            return 0
        if a < 0:
            return b
        if b < 0:
            return a
        if a < b:
            return a
        else:
            return b
        
    def n_way(self, n : int, speed : float, bullets : pg.sprite.Group, bird : Bird):
        x, y = calc_orientation(self.rect, bird.rect)
        angle0 = int(math.degrees(math.atan2(y, x)))
        for angle in range(0+angle0, 360+angle0, 360//n):
            bullets.add(Bullet(speed, angle, self))
    
    def predict(self, speed : float, bullets : pg.sprite.Group, bird : Bird):
        pred_x, pred_y = 0, 0
        pos_x = self.rect.centerx - bird.rect.centerx
        pos_y = self.rect.centery - bird.rect.centery
        bspeed_x = bird.speed*bird.sum_mv[0]
        bspeed_y = bird.speed*bird.sum_mv[1]
        l = math.sqrt(pos_x**2 + pos_y**2)
        v = math.sqrt(bspeed_x**2 + bspeed_y**2)
        t1, t2 = 0, 0
        ang1 = abs(math.degrees(math.atan2(bird.sum_mv[1], bird.sum_mv[0])))
        ang2 = abs(math.degrees(math.atan2(pos_y, pos_x)))
        if abs(ang1 - ang2) > 180:
            ang = 360 - abs(ang1 - ang2)
        else:
            ang = abs(ang1 - ang2)
        
        t1 = l / (-speed*math.sqrt(1 - ((v/speed)*math.sin(ang))**2) - v*math.cos(ang))
        t2 = l / (speed*math.sqrt(1 - ((v/speed)*math.sin(ang))**2) - v*math.cos(ang))
        t = self.PlusMin(t1, t2)
        
        pred_x = bird.rect.centerx + bspeed_x*t
        pred_y = bird.rect.centery + bspeed_y*t

        x_diff, y_diff = (pred_x-self.rect.centerx), (pred_y-self.rect.centery)
        norm = math.sqrt(x_diff**2+y_diff**2)
        angle = int(math.degrees(math.atan2(y_diff/norm, x_diff/norm)))
        bullets.add(Bullet(speed, angle, self))


class Bullet(pg.sprite.Sprite):
    def __init__(self, speed : float, angle : float, emy2 : Enemy2):
        super().__init__()
        rad = 10
        self.image = pg.Surface((2*rad, 2*rad))
        color = (random.randint(50, 100), random.randint(100, 150), random.randint(50, 100))
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # self.pos = [boss.rect.centerx, boss.rect.centery]
        self.speed = speed
        self.vx = math.cos(math.radians(angle))
        self.vy = math.sin(math.radians(angle))
        self.rect.centerx = emy2.rect.centerx
        self.rect.centery = emy2.rect.centery
        self.state="active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        # self.pos[0] += self.speed*self.vx
        # self.pos[1] += self.speed*self.vy
        # screen.blit(self.image, self.pos)
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emy2s = pg.sprite.Group()
    bullets = pg.sprite.Group()
    gravitys = pg.sprite.Group()
    shields = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        mode = 0
        if key_lst[pg.K_LSHIFT]:
            mode = 1
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if not mode:
                    beams.add(Beam(bird))
                else:
                    neobeam = NeoBeam(bird, 7)
                    for beam in neobeam.gen_beams():
                        beams.add(beam)
                
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value > 20:
                    EMP(emys, bombs, screen)
                    score.value-=20
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value >= 200:
                    score.value -= 200
                    gravitys.add(Gravity(400))
            if event.type == pg.KEYDOWN and event.key == pg.K_v:
                if score.value >= 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(Shield(bird, 400))
        screen.blit(bg_img, [0, 0])

        if tmr%1300 == 9:
            emy2s.add(Enemy2())
        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
        
        for emy2 in pg.sprite.groupcollide(emy2s, beams, False, True):
            emy2.life -= 1
            score.value += 5
            if emy2.life < 0:
                emy2.kill()
                exps.add(Explosion(emy2, 200))
                score.value += 200
        
        for emy in pg.sprite.groupcollide(emys, gravitys, True, False).keys():
            exps.add(Explosion(emy, 50))
            score.value += 10
        for bomb in pg.sprite.groupcollide(bombs, gravitys, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1
        for bullet in pg.sprite.groupcollide(bullets, gravitys, True, False):
            pass

        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1
        for bullet in pg.sprite.groupcollide(bullets, shields, True, False):
            pass


        bird.update(key_lst, screen, score)
            
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1
            else:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
            
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bomb.state == "inactive":
                continue
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return
        
        for bullet in pg.sprite.spritecollide(bird, bullets, True):
            if bird.state == "hyper":
                continue
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        emy2s.update(bullets, bird)
        emy2s.draw(screen)
        bullets.update()
        bullets.draw(screen)
        bombs.update()
        bombs.draw(screen)
        shields.update()
        shields.draw(screen)
        exps.update()
        exps.draw(screen)
        gravitys.update()
        gravitys.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    print()
    pg.quit()
    sys.exit()