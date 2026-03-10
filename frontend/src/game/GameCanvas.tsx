import { useEffect, useRef } from 'react'
import Phaser from 'phaser'
import type { Agent } from '../api/simulations'

// Asset base path (served from frontend/public/assets/)
const ASSETS = '/assets/the_ville/visuals'
const TILE_WIDTH = 32

// ─── Bridge: shared mutable state between React and Phaser ───────────────────

interface AgentTarget {
  targetX: number
  targetY: number
  pronunciatio: string
}

interface SceneBridge {
  scene: Phaser.Scene | null
  agentTargets: Map<string, AgentTarget>
  agentSprites: Map<string, Phaser.Physics.Arcade.Sprite>
  agentLabels: Map<string, Phaser.GameObjects.Text>
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  const first = parts[0]?.[0] ?? ''
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : ''
  return (first + last).toUpperCase()
}

function createAgentSprite(
  scene: Phaser.Scene,
  bridge: SceneBridge,
  agentId: string,
  target: AgentTarget,
): void {
  if (bridge.agentSprites.has(agentId)) return

  const sprite = scene.physics.add
    .sprite(target.targetX, target.targetY, 'atlas', 'misa-front')
    .setSize(30, 40)
    .setOffset(0, 32)
    .setDepth(1)

  const label = scene.add
    .text(target.targetX - 6, target.targetY - 74, target.pronunciatio, {
      font: '14px monospace',
      color: '#000000',
      padding: { x: 6, y: 4 },
      backgroundColor: '#ffffffcc',
    })
    .setDepth(3)

  bridge.agentSprites.set(agentId, sprite)
  bridge.agentLabels.set(agentId, label)
}

// ─── Component ───────────────────────────────────────────────────────────────

export interface GameCanvasProps {
  /** Optional CSS class for the wrapper div */
  className?: string
  /** Agents to render as sprites on the map */
  agents?: Agent[]
}

/**
 * GameCanvas wraps a Phaser 3 game instance inside a React component.
 * The game is initialised on mount and destroyed on unmount (no memory leaks).
 * Pass `agents` to render agent sprites on the map; updates are picked up each frame.
 */
export default function GameCanvas({ className, agents }: GameCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const gameRef = useRef<Phaser.Game | null>(null)

  // Bridge: React writes targets here; Phaser reads each frame
  const bridgeRef = useRef<SceneBridge>({
    scene: null,
    agentTargets: new Map(),
    agentSprites: new Map(),
    agentLabels: new Map(),
  })

  // ── Update agent targets when React agents prop changes ──────────────────
  useEffect(() => {
    if (!agents) return
    const bridge = bridgeRef.current
    for (const agent of agents) {
      if (!agent.location) continue
      const targetX = agent.location.x * TILE_WIDTH
      const targetY = agent.location.y * TILE_WIDTH
      bridge.agentTargets.set(agent.id, {
        targetX,
        targetY,
        pronunciatio: getInitials(agent.name),
      })
    }
    // Phaser's update() will create/move sprites on the next frame
  }, [agents])

  // ── Initialise Phaser game once on mount ─────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || gameRef.current) return

    const bridge = bridgeRef.current

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
      this.load.atlas(
        'atlas',
        'https://mikewesthad.github.io/phaser-3-tilemap-blog-posts/post-1/assets/atlas/atlas.png',
        'https://mikewesthad.github.io/phaser-3-tilemap-blog-posts/post-1/assets/atlas/atlas.json',
      )
    }

    function create(this: Phaser.Scene) {
      bridge.scene = this

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
      const CuteRPG_Mountains_B = map.addTilesetImage(
        'CuteRPG_Mountains_B',
        'CuteRPG_Mountains_B',
      )
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
      map.createLayer(
        'Wall',
        [CuteRPG_Field_C, walls].filter((t): t is Phaser.Tilemaps.Tileset => t !== null),
        0,
        0,
      )
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

      // Walking animations
      const anims = this.anims
      anims.create({
        key: 'misa-left-walk',
        frames: anims.generateFrameNames('atlas', {
          prefix: 'misa-left-walk.',
          start: 0,
          end: 3,
          zeroPad: 3,
        }),
        frameRate: 4,
        repeat: -1,
      })
      anims.create({
        key: 'misa-right-walk',
        frames: anims.generateFrameNames('atlas', {
          prefix: 'misa-right-walk.',
          start: 0,
          end: 3,
          zeroPad: 3,
        }),
        frameRate: 4,
        repeat: -1,
      })
      anims.create({
        key: 'misa-front-walk',
        frames: anims.generateFrameNames('atlas', {
          prefix: 'misa-front-walk.',
          start: 0,
          end: 3,
          zeroPad: 3,
        }),
        frameRate: 4,
        repeat: -1,
      })
      anims.create({
        key: 'misa-back-walk',
        frames: anims.generateFrameNames('atlas', {
          prefix: 'misa-back-walk.',
          start: 0,
          end: 3,
          zeroPad: 3,
        }),
        frameRate: 4,
        repeat: -1,
      })

      // Camera: follows invisible player sprite (keyboard pan)
      const player = this.physics.add
        .sprite(800, 288, 'atlas', 'misa-front')
        .setSize(30, 40)
        .setOffset(0, 0)
      player.setDepth(-1)

      const camera = this.cameras.main
      camera.startFollow(player)
      camera.setBounds(0, 0, map.widthInPixels, map.heightInPixels)

      const cursors = this.input.keyboard!.createCursorKeys()
      this.data.set('player', player)
      this.data.set('cursors', cursors)

      // Create sprites for any agents that arrived before the scene was ready
      for (const [id, target] of bridge.agentTargets) {
        createAgentSprite(this, bridge, id, target)
      }
    }

    function update(this: Phaser.Scene) {
      // Camera pan via arrow keys
      const player = this.data.get('player') as Phaser.Physics.Arcade.Sprite
      const cursors = this.data.get('cursors') as Phaser.Types.Input.Keyboard.CursorKeys
      if (player && cursors) {
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

      // Create any newly discovered agents and update sprite positions
      for (const [id, target] of bridge.agentTargets) {
        if (!bridge.agentSprites.has(id)) {
          createAgentSprite(this, bridge, id, target)
        }

        const sprite = bridge.agentSprites.get(id)
        const label = bridge.agentLabels.get(id)
        if (!sprite) continue

        const body = sprite.body as Phaser.Physics.Arcade.Body
        const MOVEMENT_SPEED = 4
        const dx = target.targetX - body.x
        const dy = target.targetY - body.y

        // Animate sprite toward target position
        if (Math.abs(dx) > MOVEMENT_SPEED || Math.abs(dy) > MOVEMENT_SPEED) {
          if (Math.abs(dx) >= Math.abs(dy)) {
            body.setVelocityX(dx > 0 ? MOVEMENT_SPEED * 60 : -MOVEMENT_SPEED * 60)
            body.setVelocityY(0)
            sprite.anims.play(dx > 0 ? 'misa-right-walk' : 'misa-left-walk', true)
          } else {
            body.setVelocityY(dy > 0 ? MOVEMENT_SPEED * 60 : -MOVEMENT_SPEED * 60)
            body.setVelocityX(0)
            sprite.anims.play(dy > 0 ? 'misa-front-walk' : 'misa-back-walk', true)
          }
        } else {
          body.setVelocity(0)
          body.reset(target.targetX, target.targetY)
          sprite.anims.stop()
          sprite.setTexture('atlas', 'misa-front')
        }

        label?.setPosition(body.x - 6, body.y - 74)
        label?.setText(target.pronunciatio)
      }
    }

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
      bridge.scene = null
      bridge.agentSprites.clear()
      bridge.agentLabels.clear()
    }
  }, []) // runs once on mount

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '100%' }}
    />
  )
}
