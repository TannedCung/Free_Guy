import { useEffect, useRef } from 'react'
import Phaser from 'phaser'

// Asset base path (served from frontend/public/assets/)
const ASSETS = '/assets/the_ville/visuals'

function preload(this: Phaser.Scene) {
  this.load.image('blocks_1', `${ASSETS}/map_assets/blocks/blocks_1.png`)
  this.load.image('walls', `${ASSETS}/map_assets/v1/Room_Builder_32x32.png`)
  this.load.image('interiors_pt1', `${ASSETS}/map_assets/v1/interiors_pt1.png`)
  this.load.image('interiors_pt2', `${ASSETS}/map_assets/v1/interiors_pt2.png`)
  this.load.image('interiors_pt3', `${ASSETS}/map_assets/v1/interiors_pt3.png`)
  this.load.image('interiors_pt4', `${ASSETS}/map_assets/v1/interiors_pt4.png`)
  this.load.image('interiors_pt5', `${ASSETS}/map_assets/v1/interiors_pt5.png`)
  this.load.image(
    'CuteRPG_Field_B',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Field_B.png`,
  )
  this.load.image(
    'CuteRPG_Field_C',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Field_C.png`,
  )
  this.load.image(
    'CuteRPG_Harbor_C',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Harbor_C.png`,
  )
  this.load.image(
    'CuteRPG_Village_B',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Village_B.png`,
  )
  this.load.image(
    'CuteRPG_Forest_B',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Forest_B.png`,
  )
  this.load.image(
    'CuteRPG_Desert_C',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Desert_C.png`,
  )
  this.load.image(
    'CuteRPG_Mountains_B',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Mountains_B.png`,
  )
  this.load.image(
    'CuteRPG_Desert_B',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Desert_B.png`,
  )
  this.load.image(
    'CuteRPG_Forest_C',
    `${ASSETS}/map_assets/cute_rpg_word_VXAce/tilesets/CuteRPG_Forest_C.png`,
  )

  this.load.tilemapTiledJSON('map', `${ASSETS}/the_ville_jan7.json`)

  // Player/agent atlas (hosted externally in original codebase)
  this.load.atlas(
    'atlas',
    'https://mikewesthad.github.io/phaser-3-tilemap-blog-posts/post-1/assets/atlas/atlas.png',
    'https://mikewesthad.github.io/phaser-3-tilemap-blog-posts/post-1/assets/atlas/atlas.json',
  )
}

function create(this: Phaser.Scene) {
  const map = this.make.tilemap({ key: 'map' })

  const collisions = map.addTilesetImage('blocks', 'blocks_1')
  const walls = map.addTilesetImage('Room_Builder_32x32', 'walls')
  const interiors_pt1 = map.addTilesetImage('interiors_pt1', 'interiors_pt1')
  const interiors_pt2 = map.addTilesetImage('interiors_pt2', 'interiors_pt2')
  const interiors_pt3 = map.addTilesetImage('interiors_pt3', 'interiors_pt3')
  const interiors_pt4 = map.addTilesetImage('interiors_pt4', 'interiors_pt4')
  const interiors_pt5 = map.addTilesetImage('interiors_pt5', 'interiors_pt5')
  const CuteRPG_Field_B = map.addTilesetImage('CuteRPG_Field_B', 'CuteRPG_Field_B')
  const CuteRPG_Field_C = map.addTilesetImage('CuteRPG_Field_C', 'CuteRPG_Field_C')
  const CuteRPG_Harbor_C = map.addTilesetImage('CuteRPG_Harbor_C', 'CuteRPG_Harbor_C')
  const CuteRPG_Village_B = map.addTilesetImage('CuteRPG_Village_B', 'CuteRPG_Village_B')
  const CuteRPG_Forest_B = map.addTilesetImage('CuteRPG_Forest_B', 'CuteRPG_Forest_B')
  const CuteRPG_Desert_C = map.addTilesetImage('CuteRPG_Desert_C', 'CuteRPG_Desert_C')
  const CuteRPG_Mountains_B = map.addTilesetImage('CuteRPG_Mountains_B', 'CuteRPG_Mountains_B')
  const CuteRPG_Desert_B = map.addTilesetImage('CuteRPG_Desert_B', 'CuteRPG_Desert_B')
  const CuteRPG_Forest_C = map.addTilesetImage('CuteRPG_Forest_C', 'CuteRPG_Forest_C')

  const tileset_group_1 = [
    CuteRPG_Field_B,
    CuteRPG_Field_C,
    CuteRPG_Harbor_C,
    CuteRPG_Village_B,
    CuteRPG_Forest_B,
    CuteRPG_Desert_C,
    CuteRPG_Mountains_B,
    CuteRPG_Desert_B,
    CuteRPG_Forest_C,
    interiors_pt1,
    interiors_pt2,
    interiors_pt3,
    interiors_pt4,
    interiors_pt5,
    walls,
  ].filter((t): t is Phaser.Tilemaps.Tileset => t !== null)

  map.createLayer('Bottom Ground', tileset_group_1, 0, 0)
  map.createLayer('Exterior Ground', tileset_group_1, 0, 0)
  map.createLayer('Exterior Decoration L1', tileset_group_1, 0, 0)
  map.createLayer('Exterior Decoration L2', tileset_group_1, 0, 0)
  map.createLayer('Interior Ground', tileset_group_1, 0, 0)
  map.createLayer('Wall', [CuteRPG_Field_C, walls].filter((t): t is Phaser.Tilemaps.Tileset => t !== null), 0, 0)
  map.createLayer('Interior Furniture L1', tileset_group_1, 0, 0)
  const interiorFurnitureL2 = map.createLayer('Interior Furniture L2 ', tileset_group_1, 0, 0)
  const foregroundL1 = map.createLayer('Foreground L1', tileset_group_1, 0, 0)
  const foregroundL2 = map.createLayer('Foreground L2', tileset_group_1, 0, 0)
  foregroundL1?.setDepth(2)
  foregroundL2?.setDepth(2)
  interiorFurnitureL2?.setDepth(1)

  if (collisions) {
    const collisionsLayer = map.createLayer('Collisions', collisions, 0, 0)
    collisionsLayer?.setCollisionByProperty({ collide: true })
    collisionsLayer?.setDepth(-1)
  }

  // Camera follows an invisible player sprite (keyboard pan)
  const player = this.physics.add.sprite(800, 288, 'atlas', 'misa-front').setSize(30, 40).setOffset(0, 0)
  player.setDepth(-1)

  const camera = this.cameras.main
  camera.startFollow(player)
  camera.setBounds(0, 0, map.widthInPixels, map.heightInPixels)

  const cursors = this.input.keyboard!.createCursorKeys()

  // Store references for use in update
  this.data.set('player', player)
  this.data.set('cursors', cursors)

  // Walking animations
  const anims = this.anims
  anims.create({
    key: 'misa-left-walk',
    frames: anims.generateFrameNames('atlas', { prefix: 'misa-left-walk.', start: 0, end: 3, zeroPad: 3 }),
    frameRate: 4,
    repeat: -1,
  })
  anims.create({
    key: 'misa-right-walk',
    frames: anims.generateFrameNames('atlas', { prefix: 'misa-right-walk.', start: 0, end: 3, zeroPad: 3 }),
    frameRate: 4,
    repeat: -1,
  })
  anims.create({
    key: 'misa-front-walk',
    frames: anims.generateFrameNames('atlas', { prefix: 'misa-front-walk.', start: 0, end: 3, zeroPad: 3 }),
    frameRate: 4,
    repeat: -1,
  })
  anims.create({
    key: 'misa-back-walk',
    frames: anims.generateFrameNames('atlas', { prefix: 'misa-back-walk.', start: 0, end: 3, zeroPad: 3 }),
    frameRate: 4,
    repeat: -1,
  })
}

function update(this: Phaser.Scene) {
  const player = this.data.get('player') as Phaser.Physics.Arcade.Sprite
  const cursors = this.data.get('cursors') as Phaser.Types.Input.Keyboard.CursorKeys
  if (!player || !cursors) return

  const body = player.body as Phaser.Physics.Arcade.Body
  const speed = 400
  body.setVelocity(0)

  if (cursors.left.isDown) {
    body.setVelocityX(-speed)
    player.anims.play('misa-left-walk', true)
  } else if (cursors.right.isDown) {
    body.setVelocityX(speed)
    player.anims.play('misa-right-walk', true)
  } else if (cursors.up.isDown) {
    body.setVelocityY(-speed)
    player.anims.play('misa-back-walk', true)
  } else if (cursors.down.isDown) {
    body.setVelocityY(speed)
    player.anims.play('misa-front-walk', true)
  } else {
    player.anims.stop()
    player.setTexture('atlas', 'misa-front')
  }
}

interface GameCanvasProps {
  /** Optional CSS class for the wrapper div */
  className?: string
}

/**
 * GameCanvas wraps a Phaser 3 game instance inside a React component.
 * The game is initialised on mount and destroyed on unmount (no memory leaks).
 */
export default function GameCanvas({ className }: GameCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const gameRef = useRef<Phaser.Game | null>(null)

  useEffect(() => {
    if (!containerRef.current || gameRef.current) return

    const config: Phaser.Types.Core.GameConfig = {
      type: Phaser.AUTO,
      width: 4300,
      height: 2800,
      parent: containerRef.current,
      pixelArt: true,
      physics: {
        default: 'arcade',
        arcade: { gravity: { x: 0, y: 0 } },
      },
      scene: { preload, create, update },
      scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
    }

    gameRef.current = new Phaser.Game(config)

    return () => {
      gameRef.current?.destroy(true)
      gameRef.current = null
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '100%' }}
    />
  )
}
