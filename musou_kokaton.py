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
    def __init__(self, bird: Bird, angle0 : float = 0, a=2.0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        self.angle = angle0 + math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, a)
        self.vx = math.cos(math.radians(self.angle))
        self.vy = -math.sin(math.radians(self.angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        self.time = 0

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        if self.time > 0:
                print(self.time)
                
                self.time -= 1
                self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, 6.0)
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


#itemに関するクラス
class Spanner(pg.sprite.Sprite):
    

    def __init__(self, obj: "Enemy"):
        """
        アイテムを生成する
        引数1 obj：爆発する敵機インスタンス
        """
        super().__init__()
        img = pg.image.load(f"fig/spanner.png")
        self.image = pg.transform.scale(img, (img.get_width() * 0.1, img.get_height() * 0.1)) #画像を縮小
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.speed = 3
        self.time = 500


    def update(self):
        self.rect.y += self.speed #下方向に落下
    

class Doublescore(pg.sprite.Sprite):
    def __init__(self, obj: "Enemy"):
        """
        アイテムを生成する
        引数1 obj：爆発する敵機インスタンス
        """
        super().__init__()
        img = pg.image.load(f"fig/double.png")
        self.image = pg.transform.scale(img, (img.get_width() * 0.03, img.get_height() * 0.03)) #画像を縮小
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.speed = 3

    def update(self):
        self.rect.y += self.speed #下方向に落下


class color():
    def __init__(self):
        self.image=pg.Surface((1000, 600))
        pg.draw.rect(self.image,(255, 255, 255),(0, 0), )


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
    gravitys = pg.sprite.Group()
    shields = pg.sprite.Group()
    spanners = pg.sprite.Group()
    doublescores = pg.sprite.Group()
    time = 0

    tmr = 0
    rand = 0

    clock = pg.time.Clock()
    while True:
        print(time)
        key_lst = pg.key.get_pressed()
        mode = 0
        if key_lst[pg.K_LSHIFT]:
            mode = 1
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if not mode:
                    
                    if time > 0: 
                        beams.add(Beam(bird,a=6))
                        time -= 1
                        print(time)
                    else:
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
            rand = random.randint(1,2)  #4分の1の確率でアイテム生成
            if rand == 1:
                spanners.add(Spanner(emy))
            elif rand == 2:
                doublescores.add(Doublescore(emy))

        for spanner in pg.sprite.spritecollide(bird, spanners, True):
            time = 10
            bird.change_img(6.1, screen)  # こうかとん覚醒エフェクト
            #state = "hyper"
            
            
            
            
            # if state == "hyper":   # 無敵状態のとき
            #     hyper_life -= 1
            #     if hyper_life < 0:
            #         state = "normal"
            
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:    
                neobeam = NeoBeam(bird, 7)
                for beam in neobeam.gen_beams():
                    beams.add(beam)


        for doublescore in pg.sprite.spritecollide(bird, doublescores, True):
            bird.change_img(6, screen)   # こうかとん喜びエフェクト
            score.value *= 2  # 2倍点アップ



        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
        
        for emy in pg.sprite.groupcollide(emys, gravitys, True, False).keys():
            exps.add(Explosion(emy, 50))
            score.value += 10
        for bomb in pg.sprite.groupcollide(bombs, gravitys, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

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
        

        

        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        shields.update()
        shields.draw(screen)
        exps.update()
        exps.draw(screen)
        gravitys.update()
        gravitys.draw(screen)
        score.update(screen)
        spanners.update()
        spanners.draw(screen)
        doublescores.update()
        doublescores.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    print()
    pg.quit()
    sys.exit()