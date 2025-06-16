# 微信小程序AI聊天室后端API规格文档

## 📋 项目概述

基于微信小程序的AI聊天室产品，采用多维度MBTI角色生态系统。用户可以在不同主题聊天室中与64种不同性格背景的AI角色互动，通过"认同"机制和话题互动提升角色技能，解锁更多角色和技能，创造个性化的AI伙伴成长体验。

---

## 🏗️ 核心功能架构
### 聊天室系统
- **多主题聊天室**：金融投资、娱乐休闲、每日记事等主题
- **AI角色配置**：每个聊天室包含3-5个不同专业的AI角色
- **动态交互**：基于用户认同度的AI活跃度调节机制
### 多维度MBTI角色系统
- **16种MBTI维度**：每种性格类型对应4个不同背景的角色，共64个角色
- **角色示例**：
  ```
  INTJ维度（4个角色）：
  ├── 🔬 科学家 (理性研究型) - 免费基础角色
  ├── 🏗️ 建筑师 (设计创造型) - 付费角色 ¥12
  ├── 💻 程序员 (技术逻辑型) - VIP专属
  └── 🎯 战略家 (规划决策型) - 限定角色 ¥68
  
  ENFP维度（4个角色）：
  ├── 🎨 艺术家 (创意表达型) - 免费基础角色
  ├── 📺 主播 (社交娱乐型) - 付费角色 ¥18
  ├── 🎭 演员 (表演艺术型) - VIP专属
  └── 🌟 创意总监 (领导创新型) - 限定角色 ¥88
  ```

### 智能技能成长系统
- **天赋技能**：每个角色的初始专长，不同等级解锁不同能力
- **学习技能**：通过在聊天室互动、话题匹配度、获得认同等方式习得
- **技能升级**：基于话题相关性自动积累经验值，或付费快速升级

### 认同与成长机制
- **认同系统**：用户对AI回复进行认同，影响角色活跃度和技能经验
- **话题匹配**：AI回复与聊天话题相关性越高，技能经验提升越多
- **成长追踪**：详细记录每个角色的技能进度和解锁状态

---

## 👤 用户账号系统

### 用户注册登录

#### 微信登录流程
```
1. 小程序调用 wx.login() 获取 code
2. 前端请求: POST /api/auth/wxlogin
3. 后端通过 code 获取 openid 和 session_key
4. 返回自定义 token 和用户信息
```

#### 微信登录接口
```http
POST /api/auth/wxlogin
Content-Type: application/json

Request:
{
  "code": "string",           // 微信登录凭证
  "nickName": "string",       // 用户昵称
  "avatarUrl": "string",      // 用户头像URL
  "gender": 0,                // 性别 0未知 1男 2女
  "country": "string",        // 国家
  "province": "string",       // 省份
  "city": "string"           // 城市
}

Response:
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "jwt_token_string",
    "expiresIn": 7200,         // token过期时间(秒)
    "user": {
      "userId": "string",
      "openid": "string",
      "nickName": "string",
      "avatarUrl": "string",
      "userLevel": "normal",    // normal|vip|premium
      "createTime": "timestamp",
      "lastLoginTime": "timestamp",
      "isNewUser": true         // 是否新用户
    },
    "defaultCharacters": [     // 新用户默认解锁的16个免费角色
      {
        "characterId": "intj_scientist_001",
        "dimension": "INTJ",
        "name": "艾米·科学家",
        "isDefault": true
      }
    ]
  }
}
```

### 用户信息管理

#### 获取用户信息
```http
GET /api/user/profile
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "userId": "string",
    "openid": "string",
    "nickName": "string", 
    "avatarUrl": "string",
    "gender": 0,
    "country": "string",
    "province": "string", 
    "city": "string",
    "userLevel": "normal",      // 用户等级
    "totalMessages": 156,       // 总消息数
    "totalLikes": 89,          // 获得的总认同数
    "ownedCharacters": 18,     // 拥有角色数量
    "totalSkillLevel": 156,    // 所有技能等级总和
    "joinedRooms": [           // 已加入房间
      {
        "roomId": "finance_room",
        "joinTime": "timestamp",
        "lastActiveTime": "timestamp"
      }
    ],
    "favoriteCharacters": [    // 收藏的角色
      {
        "characterId": "intj_scientist_001",
        "name": "艾米·科学家",
        "level": 15,
        "totalSkillLevel": 23
      }
    ],
    "createTime": "timestamp",
    "lastLoginTime": "timestamp"
  }
}
```

#### 更新用户信息
```http
PUT /api/user/profile
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "nickName": "string",       // 可选
  "avatarUrl": "string",      // 可选
  "gender": 1                 // 可选
}

Response:
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "user": {...}             // 更新后的用户信息
  }
}
```

### 用户等级系统

#### 等级规则
- **normal**：普通用户，基础功能
- **vip**：VIP用户，高级AI角色、更多聊天次数
- **premium**：高级用户，所有功能、专属AI角色

#### 获取用户统计
```http
GET /api/user/stats
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "userId": "string",
    "userLevel": "normal",
    "currentLevelExp": 1250,    // 当前等级经验
    "nextLevelExp": 2000,       // 升级所需经验
    "statistics": {
      "totalMessages": 156,     // 总发言数
      "totalLikes": 89,         // 总认同数  
      "totalDays": 15,          // 使用天数
      "roomsCount": 3,          // 参与房间数
      "favoriteAICount": 2      // 收藏AI数量
    },
    "achievements": [           // 成就列表
      {
        "achievementId": "first_message",
        "name": "初出茅庐",
        "description": "发送第一条消息",
        "unlockTime": "timestamp"
      }
    ],
    "weeklyStats": {            // 本周统计
      "messagesCount": 25,
      "likesReceived": 12,
      "likesGiven": 18,
      "activeHours": 5.5
    }
  }
}
```

### Token管理

#### 刷新Token
```http
POST /api/auth/refresh
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "token": "new_jwt_token",
    "expiresIn": 7200
  }
}
```

#### 退出登录
```http
POST /api/auth/logout
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "退出成功"
}
```

---

## 🤖 多维度角色系统

### 角色数据结构
```json
{
  "characterId": "intj_scientist_001",
  "dimension": "INTJ",        // MBTI维度
  "name": "艾米·科学家",
  "englishName": "Amy Scientist",
  "avatar": "/static/characters/intj_scientist.svg",
  "background": "科学家",
  "backgroundStory": "毕业于斯坦福大学的数据科学博士，专注于复杂系统分析...",
  "rarity": "common",         // common|rare|epic|legendary
  "unlockType": "free",       // free|paid|vip|limited
  "price": 0,                 // 0=免费, >0=付费价格
  
  "personality": {
    "traits": ["理性", "独立", "追求真理", "完美主义"],
    "catchphrase": "数据不会撒谎，但解读数据需要智慧",
    "communication": "逻辑清晰，喜欢用事实和数据说话",
    "quirks": ["喜欢用比喻解释复杂概念", "偶尔会陷入思考忘记回复"]
  },
  
  "talents": [                // 天赋技能（初始拥有）
    {
      "skillId": "data_analysis",
      "skillName": "数据分析",
      "level": 1,
      "maxLevel": 10,
      "experience": 0,
      "description": "天生擅长分析复杂数据和发现规律",
      "effects": {
        "level1": "基础数据解读能力",
        "level5": "高级统计分析能力", 
        "level10": "预测建模大师级能力"
      }
    },
    {
      "skillId": "logical_reasoning", 
      "skillName": "逻辑推理",
      "level": 1,
      "maxLevel": 10,
      "experience": 0,
      "description": "严密的逻辑思维和推理能力"
    }
  ],
  
  "learnableSkills": [         // 可学习技能
    {
      "skillId": "investment_analysis", 
      "skillName": "投资分析",
      "level": 0,
      "maxLevel": 10,
      "experience": 0,
      "unlockCondition": {
        "type": "topic_interaction",
        "topics": ["投资", "股票", "基金", "理财"],
        "requirement": 50,       // 需要在相关话题互动50次
        "description": "在投资相关话题中积极互动"
      },
      "upgradeConditions": [
        {
          "level": 2,
          "requirements": [
            {"type": "topic_experience", "value": 100},
            {"type": "likes_received", "value": 20}
          ],
          "fastUpgrade": {"cost": 6, "currency": "CNY"}
        },
        {
          "level": 5,
          "requirements": [
            {"type": "topic_experience", "value": 500},
            {"type": "likes_received", "value": 100},
            {"type": "consecutive_days", "value": 7}
          ],
          "fastUpgrade": {"cost": 18, "currency": "CNY"}
        }
      ]
    },
    {
      "skillId": "game_strategy",
      "skillName": "游戏策略", 
      "level": 0,
      "maxLevel": 10,
      "experience": 0,
      "unlockCondition": {
        "type": "room_interaction",
        "roomId": "entertainment_room",
        "requirement": 30,
        "description": "在娱乐休闲室互动30次"
      }
    }
  ],
  
  "statistics": {
    "totalMessages": 1256,
    "totalLikes": 890,
    "averageResponseTime": 2.5,
    "userRating": 4.8,
    "topicExpertise": {         // 话题专长度
      "investment": 0.85,
      "technology": 0.92,
      "science": 0.95,
      "gaming": 0.45
    }
  },
  
  "isEnabled": true,
  "createTime": "timestamp",
  "updateTime": "timestamp"
}
```

### 技能经验计算系统
```json
{
  "experienceRules": {
    "topicMatch": {
      "description": "基于话题匹配度获得经验",
      "calculation": "messageLength * topicRelevance * difficultyMultiplier",
      "factors": {
        "topicRelevance": "0.1-1.0 (AI判断回复与技能话题的相关度)",
        "difficultyMultiplier": "1.0-2.0 (复杂话题获得更多经验)",
        "baseExperience": "1-10 (根据消息长度和质量)"
      }
    },
    "userInteraction": {
      "like": 5,              // 每个认同+5经验
      "reply": 3,             // 用户回复+3经验
      "mention": 8,           // 被@提及+8经验
      "consecutive": 1.2      // 连续对话乘数
    },
    "roomBonus": {
      "description": "特定房间内相关技能经验加成",
      "finance_room": {
        "investment_analysis": 1.5,
        "data_analysis": 1.2
      },
      "entertainment_room": {
        "game_strategy": 1.5,
        "social_interaction": 1.3
      }
    }
  }
}
```

### HTTP API接口

#### 获取用户角色库
```http
GET /api/user/characters
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "ownedCharacters": [
      {
        "characterId": "intj_scientist_001",
        "dimension": "INTJ",
        "name": "艾米·科学家",
        "level": 15,
        "experience": 2580,
        "nextLevelExp": 3000,
        "avatar": "/static/characters/intj_scientist.svg",
        "talents": [...],
        "learnedSkills": [...],
        "isActive": true        // 是否正在使用
      }
    ],
    "availableCharacters": [   // 可解锁但未拥有的角色
      {
        "characterId": "intj_architect_002", 
        "dimension": "INTJ",
        "name": "大卫·建筑师",
        "unlockType": "paid",
        "price": 12,
        "preview": {...}       // 预览信息
      }
    ],
    "lockedCharacters": [      // 暂未满足解锁条件的角色
      {
        "characterId": "intj_strategist_004",
        "name": "莉莉·战略家",
        "unlockCondition": "VIP等级",
        "preview": {...}
      }
    ]
  }
}
```

#### 获取角色详情
```http
GET /api/characters/{characterId}
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "character": {
      "characterId": "intj_scientist_001",
      "dimension": "INTJ",
      "name": "艾米·科学家",
      "avatar": "/static/characters/intj_scientist.svg",
      "background": "科学家",
      "backgroundStory": "...",
      "personality": {...},
      "talents": [...],
      "learnableSkills": [...],
      "statistics": {...}
    },
    "userProgress": {          // 用户对此角色的使用情况
      "level": 15,
      "experience": 2580,
      "nextLevelExp": 3000,
      "skillProgress": [
        {
          "skillId": "investment_analysis",
          "level": 3,
          "experience": 245,
          "nextLevelExp": 300,
          "canUpgrade": true,
          "fastUpgradeCost": 6
        }
      ],
      "recentAchievements": [
        "投资分析师", "连续对话7天", "获得100个认同"
      ]
    }
  }
}
```

#### 角色商店
```http
GET /api/shop/characters?dimension=INTJ&category=paid&page=1&pageSize=12
Authorization: Bearer {token}

Query Parameters:
- dimension: INTJ|ENFP|ISTP|... (MBTI维度筛选)
- category: all|free|paid|vip|limited (类别筛选)
- rarity: all|common|rare|epic|legendary (稀有度筛选)
- sort: price|popularity|newest (排序方式)

Response:
{
  "code": 200,
  "data": {
    "characters": [
      {
        "characterId": "intj_architect_002",
        "dimension": "INTJ", 
        "name": "大卫·建筑师",
        "avatar": "/static/characters/intj_architect.svg",
        "background": "建筑师",
        "rarity": "rare",
        "unlockType": "paid",
        "price": 12,
        "originalPrice": 18,   // 原价（如有折扣）
        "discount": 0.33,      // 折扣
        "preview": {
          "talents": ["空间设计", "美学感知"],
          "specialSkills": ["建筑分析", "设计思维"],
          "sampleDialogue": "让我们从结构和美学的角度来分析这个问题..."
        },
        "popularity": 4.8,     // 用户评分
        "purchaseCount": 1256, // 购买人数
        "isHot": true,         // 是否热门
        "isNew": false,        // 是否新品
        "tags": ["设计", "创意", "专业"]
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 12,
      "total": 48,
      "hasMore": true
    },
    "recommendations": [      // 个性化推荐
      "基于您喜欢INTJ-科学家，推荐INTJ-程序员"
    ]
  }
}
```

#### 解锁/购买角色
```http
POST /api/characters/unlock
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "characterId": "intj_architect_002",
  "unlockType": "purchase",   // purchase|free_unlock
  "paymentMethod": "wechat_pay", // 微信支付
  "couponId": "coupon_123"    // 优惠券ID（可选）
}

Response:
{
  "code": 200,
  "message": "角色解锁成功",
  "data": {
    "characterId": "intj_architect_002",
    "unlockTime": "timestamp",
    "paymentInfo": {
      "orderId": "order_123456",
      "amount": 12,
      "actualAmount": 8,     // 使用优惠券后的实际支付金额
      "paymentMethod": "wechat_pay"
    },
    "character": {...}       // 完整角色信息
  }
}
```

#### 技能升级
```http
POST /api/skills/upgrade
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "characterId": "intj_scientist_001",
  "skillId": "investment_analysis",
  "upgradeType": "natural|fast",  // 自然升级或付费快速升级
  "paymentMethod": "wechat_pay"   // 仅快速升级需要
}

Response:
{
  "code": 200,
  "message": "技能升级成功", 
  "data": {
    "skillId": "investment_analysis",
    "oldLevel": 2,
    "newLevel": 3,
    "newAbilities": [
      "解锁期货分析能力",
      "提升投资建议质量20%"
    ],
    "nextLevelRequirement": {
      "experience": 500,
      "likes": 50,
      "fastUpgradeCost": 12
    }
  }
}
```

#### 获取技能进度
```http
GET /api/skills/progress/{characterId}
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "characterId": "intj_scientist_001",
    "skillProgress": [
      {
        "skillId": "investment_analysis",
        "skillName": "投资分析",
        "level": 3,
        "experience": 245,
        "nextLevelExp": 300,
        "progress": 81.7,      // 升级进度百分比
        "canUpgrade": false,
        "upgradeRequirements": [
          {
            "type": "topic_experience",
            "current": 245,
            "required": 300,
            "description": "投资话题经验值"
          },
          {
            "type": "likes_received", 
            "current": 45,
            "required": 50,
            "description": "获得认同数"
          }
        ],
        "fastUpgrade": {
          "available": true,
          "cost": 12,
          "currency": "CNY"
        },
        "recentActivity": [
          {
            "date": "2024-01-15",
            "experienceGained": 15,
            "source": "金融投资室对话",
            "details": "讨论股票投资策略获得15点经验"
          }
        ]
      }
    ]
  }
}
```

---

## 🖼️ 首页内容接口

### 首页展示需求
- **卡片 Cards**：展示热门聊天室/功能入口，包含图标、标题、背景渐变等信息，可点击跳转。
- **轮播 Swipers**：首页顶部横幅，支持跳转指定聊天室或外部链接。

### 数据结构示例
```json
{
  "card": {
    "id": "finance_room",          // 唯一标识（通常与 roomId 相同）
    "title": "金融投资",             // 标题
    "icon": "💰",                  // Emoji 或图标 URL
    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", // 背景
    "description": "专业金融分析，投资理财建议",   // 描述
    "roomId": "finance_room",      // 跳转的聊天室 ID（可选）
    "targetUrl": ""                // 若跳转外链则填写
  },
  "swiper": {
    "id": "banner_finance_001",    // 唯一标识
    "imageUrl": "/static/banners/finance.png",  // 图片 URL（建议 750×300）
    "title": "投资热门话题",        // 标题（可选，用于无图标时覆盖文字）
    "jumpType": "room",            // room|url|none
    "roomId": "finance_room",      // 当 jumpType=room 时必填
    "targetUrl": ""                // 当 jumpType=url 时必填
  }
}
```

### HTTP API接口

#### 获取首页卡片列表
```http
GET /home/cards

Response:
{
  "code": 200,
  "data": {
    "cards": [
      {
        "id": "finance_room",
        "title": "金融投资",
        "icon": "💰",
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "description": "专业金融分析，投资理财建议",
        "roomId": "finance_room"
      },
      {
        "id": "entertainment_room",
        "title": "娱乐休闲",
        "icon": "🎮",
        "background": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "description": "轻松聊天，娱乐互动",
        "roomId": "entertainment_room"
      }
    ]
  }
}
```

#### 获取首页轮播图列表
```http
GET /home/swipers

Response:
{
  "code": 200,
  "data": {
    "swipers": [
      {
        "id": "banner_finance_001",
        "imageUrl": "/static/banners/finance.png",
        "title": "投资热门话题",
        "jumpType": "room",
        "roomId": "finance_room"
      },
      {
        "id": "banner_outside_001",
        "imageUrl": "/static/banners/promo.png",
        "jumpType": "url",
        "targetUrl": "https://example.com/activity"
      }
    ]
  }
}
```

> **说明：**
> 1. 两个接口均为 *无鉴权* 公开接口，首页首次加载即调用；如需灰度、AB 测试，可在返回结构中增加 `experimentId`。
> 2. 若希望在后台动态控制排序，可在返回数组中按业务排序返回即可。
> 3. 前端缓存本地 5 分钟，后续自动刷新。

---

## 🏠 聊天室管理

### 房间数据结构
```json
{
  "roomId": "finance_room",
  "name": "金融投资", 
  "description": "专业金融分析，投资理财建议",
  "icon": "💰",
  "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  "category": "finance",       // 房间分类
  "relatedSkills": [           // 房间相关技能
    "investment_analysis",
    "data_analysis", 
    "risk_management",
    "market_research"
  ],
  "skillBonusMultiplier": {    // 技能经验加成
    "investment_analysis": 1.5,
    "data_analysis": 1.2,
    "risk_management": 1.3
  },
  "settings": {
    "maxMembers": 50,
    "allowGuestJoin": true,    // 是否允许游客加入
    "moderationLevel": "low",  // 审核等级
    "aiResponseDelay": 2000    // AI响应延迟(毫秒)
  },
  "statistics": {
    "totalMembers": 156,       // 总成员数
    "activeCharacters": 23,    // 活跃角色数
    "skillEvolutionCount": 45  // 技能进化次数
  },
  "isActive": true,
  "createTime": "timestamp",
  "updateTime": "timestamp"
}
```

### HTTP API接口

#### 获取房间列表
```http
GET /api/rooms?category=all&page=1&pageSize=10&sort=popularity
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "rooms": [
      {
        "roomId": "finance_room",
        "name": "金融投资",
        "description": "专业金融分析，投资理财建议", 
        "icon": "💰",
        "background": "linear-gradient(...)",
        "category": "finance",
        "activeCharacters": [   // 当前房间活跃的角色
          {
            "characterId": "intj_scientist_001",
            "dimension": "INTJ",
            "avatar": "/static/characters/intj_scientist_mini.svg",
            "level": 15
          },
          {
            "characterId": "estj_manager_001",
            "dimension": "ESTJ", 
            "avatar": "/static/characters/estj_manager_mini.svg",
            "level": 12
          }
        ],
        "skillOpportunities": [  // 可提升技能提示
          "投资分析", "数据分析", "风险管理"
        ],
        "lastActivity": "timestamp",
        "isJoined": true,          // 当前用户是否已加入
        "requireLevel": "normal"   // 所需用户等级
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 10,
      "total": 25,
      "hasMore": true
    }
  }
}
```

#### 获取房间详情
```http
GET /api/rooms/{roomId}
Authorization: Bearer {token}

Response:
{
  "code": 200, 
  "data": {
    "room": {
      "roomId": "finance_room",
      "name": "金融投资",
      "description": "专业金融分析，投资理财建议",
      "icon": "💰", 
      "background": "linear-gradient(...)",
      "category": "finance",
      "activeCharacters": [
        {
          "characterId": "intj_scientist_001",
          "dimension": "INTJ",
          "avatar": "/static/characters/intj_scientist.svg", 
          "level": 15
        }
      ],
      "settings": {...},
      "statistics": {...}
    },
    "userStatus": {
      "isJoined": true,
      "joinTime": "timestamp",
      "messageCount": 25,        // 用户在此房间的消息数
      "likesGiven": 12          // 用户在此房间给出的认同数
    }
  }
}
```

#### 获取房间消息历史
```http
GET /api/rooms/{roomId}/messages?before=messageId&limit=20
Authorization: Bearer {token}

Query Parameters:
- before: 获取此消息ID之前的消息 (可选，用于分页)
- limit: 获取数量，默认20，最大50

Response:
{
  "code": 200,
  "data": {
    "messages": [
      {
        "messageId": "srv_msg_124",
        "fromType": "user|ai",
        "fromUser": {
          "userId": "user123",
          "nickName": "张三",
          "avatarUrl": "xxx"
        },
        "aiInfo": {             // 当fromType=ai时存在
          "characterId": "intj_scientist_001", 
          "name": "艾米·科学家",
          "avatar": "/static/characters/intj_scientist.svg"
        },
        "content": "今天股市怎么样？",
        "replyToMessageId": "srv_msg_123",
        "mentions": ["intj_scientist_001"],
        "likes": [
          {
            "userId": "user456",
            "nickName": "李四", 
            "timestamp": 1234567890
          }
        ],
        "totalLikes": 5,
        "isLikedByMe": true,    // 当前用户是否已认同
        "timestamp": 1234567890
      }
    ],
    "hasMore": true,
    "nextCursor": "srv_msg_100"
  }
}
```

#### 加入/退出房间
```http
POST /api/rooms/{roomId}/join
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "加入成功",
  "data": {
    "roomId": "finance_room",
    "joinTime": "timestamp"
  }
}
```

```http
POST /api/rooms/{roomId}/leave  
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "退出成功"
}
```

---

## 💰 商业化系统

### 付费模式设计
```json
{
  "monetization": {
    "characterPurchase": {
      "freeCharacters": 16,    // 每个MBTI维度1个免费角色
      "paidCharacters": {
        "rare": {"price": "¥12-18", "count": 16},
        "epic": {"price": "¥28-38", "count": 16}, 
        "legendary": {"price": "¥68-88", "count": 16}
      },
      "bundles": {
        "dimensionPack": "¥45 解锁某个MBTI维度全部4个角色",
        "rarityPack": "¥150 解锁所有rare级别角色",
        "completePack": "¥298 解锁所有64个角色"
      }
    },
    
    "skillUpgrade": {
      "naturalUpgrade": "通过互动和话题匹配免费升级",
      "fastUpgrade": {
        "level1to5": "¥6-18 跳过单级升级条件",
        "level6to10": "¥25-68 跳过单级升级条件",
        "skillMaxOut": "¥88 直接升满某个技能"
      },
      "skillPacks": {
        "characterSkillPack": "¥128 某个角色所有技能满级",
        "topicSkillPack": "¥68 某个话题相关所有技能满级"
      }
    },
    
    "vipMembership": {
      "monthly": "¥30/月",
      "yearly": "¥298/年", 
      "benefits": [
        "解锁所有VIP专属角色",
        "技能升级费用8折",
        "每日额外经验加成20%",
        "专属VIP聊天室",
        "角色形象自定义",
        "优先体验新功能"
      ]
    },
    
    "limitedOffers": {
      "seasonalCharacters": "¥128-188 节日限定角色",
      "anniversaryPack": "¥168 周年纪念礼包",
      "collaborationCharacters": "¥88-148 联名角色"
    }
  }
}
```

### 支付系统接口
```http
POST /api/payment/create-order
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "productType": "character|skill|vip|bundle",
  "productId": "intj_architect_002",
  "quantity": 1,
  "paymentMethod": "wechat_pay",
  "couponId": "coupon_123",     // 可选
  "source": "character_store"   // 购买来源
}

Response:
{
  "code": 200,
  "data": {
    "orderId": "order_123456789",
    "productInfo": {
      "name": "大卫·建筑师",
      "originalPrice": 18,
      "discountPrice": 12,
      "finalPrice": 10         // 使用优惠券后的最终价格
    },
    "paymentInfo": {
      "prepayId": "wx_prepay_123",
      "timeStamp": "timestamp",
      "nonceStr": "random_string", 
      "package": "prepay_id=wx_prepay_123",
      "signType": "RSA",
      "paySign": "signature"
    },
    "expireTime": "timestamp"  // 订单过期时间
  }
}
```

---

## 💾 数据存储结构

### 用户表 (users)
```sql
{
  "userId": "string PRIMARY KEY",
  "openid": "string UNIQUE",
  "unionid": "string",
  "nickName": "string",
  "avatarUrl": "string", 
  "gender": "int",
  "country": "string",
  "province": "string",
  "city": "string",
  "userLevel": "enum(normal,vip,premium)",
  "experience": "int DEFAULT 0",
  "totalMessages": "int DEFAULT 0",
  "totalLikes": "int DEFAULT 0",
  "totalCharacters": "int DEFAULT 16",    // 拥有角色数
  "totalSkillLevel": "int DEFAULT 0",     // 所有技能等级总和
  "lastLoginTime": "timestamp",
  "createTime": "timestamp",
  "updateTime": "timestamp",
  "isDeleted": "boolean DEFAULT false"
}
```

### 角色定义表 (character_definitions)
```sql
{
  "characterId": "string PRIMARY KEY",
  "dimension": "string",              // MBTI维度
  "name": "string",
  "englishName": "string",
  "avatar": "string",
  "background": "string",
  "backgroundStory": "text",
  "rarity": "enum(common,rare,epic,legendary)",
  "unlockType": "enum(free,paid,vip,limited)",
  "price": "decimal(10,2) DEFAULT 0",
  "personality": "json",              // 性格特征
  "talents": "json",                  // 天赋技能
  "learnableSkills": "json",          // 可学习技能
  "isEnabled": "boolean DEFAULT true",
  "createTime": "timestamp",
  "updateTime": "timestamp"
}
```

### 用户角色表 (user_characters)
```sql
{
  "id": "string PRIMARY KEY",
  "userId": "string",
  "characterId": "string",
  "level": "int DEFAULT 1",
  "experience": "int DEFAULT 0",
  "unlockTime": "timestamp",
  "unlockType": "enum(default,purchase,gift)",
  "totalMessages": "int DEFAULT 0",
  "totalLikes": "int DEFAULT 0",
  "lastActiveTime": "timestamp",
  "isActive": "boolean DEFAULT false",  // 是否当前使用
  "UNIQUE(userId, characterId)",
  "INDEX(userId, isActive)"
}
```

### 技能进度表 (skill_progress)
```sql
{
  "id": "string PRIMARY KEY",
  "userId": "string",
  "characterId": "string",
  "skillId": "string",
  "level": "int DEFAULT 0",
  "experience": "int DEFAULT 0",
  "unlockTime": "timestamp",
  "lastUpgradeTime": "timestamp",
  "totalUsageCount": "int DEFAULT 0",
  "UNIQUE(userId, characterId, skillId)",
  "INDEX(userId, characterId)"
}
```

### 技能经验记录表 (skill_experience_log)
```sql
{
  "id": "string PRIMARY KEY",
  "userId": "string",
  "characterId": "string", 
  "skillId": "string",
  "messageId": "string",           // 相关消息ID
  "roomId": "string",
  "experienceGained": "int",
  "source": "enum(topic_match,like,mention,room_bonus)",
  "topicRelevance": "float",       // 话题相关度
  "createTime": "timestamp",
  "INDEX(userId, characterId, skillId)",
  "INDEX(createTime)"
}
```

### 房间表 (rooms)
```sql
{
  "roomId": "string PRIMARY KEY",
  "name": "string",
  "description": "text",
  "icon": "string",
  "background": "string", 
  "category": "string",
  "relatedSkills": "json",         // 相关技能列表
  "skillBonusMultiplier": "json",  // 技能经验加成
  "maxMembers": "int DEFAULT 50",
  "settings": "json",
  "totalMembers": "int DEFAULT 0",
  "activeCharacters": "int DEFAULT 0",
  "skillEvolutionCount": "int DEFAULT 0",
  "isActive": "boolean DEFAULT true",
  "createTime": "timestamp",
  "updateTime": "timestamp"
}
```

### 消息表 (messages)
```sql
{
  "messageId": "string PRIMARY KEY",
  "roomId": "string",
  "fromUserId": "string",
  "fromType": "enum(user,ai)",
  "characterId": "string",         // AI角色ID（当fromType=ai时）
  "content": "text", 
  "replyToMessageId": "string",
  "mentions": "json",              // @的角色ID数组
  "skillsUsed": "json",            // 使用的技能列表
  "topicRelevance": "float",       // 话题相关度
  "experienceGained": "json",      // 获得的经验分配
  "totalLikes": "int DEFAULT 0",
  "createTime": "timestamp",
  "updateTime": "timestamp",
  "isDeleted": "boolean DEFAULT false",
  "INDEX(roomId, createTime)",
  "INDEX(fromUserId, createTime)",
  "INDEX(characterId, createTime)"
}
```

### 订单表 (orders)
```sql
{
  "orderId": "string PRIMARY KEY",
  "userId": "string",
  "productType": "enum(character,skill,vip,bundle)",
  "productId": "string",
  "productName": "string",
  "originalPrice": "decimal(10,2)",
  "discountPrice": "decimal(10,2)",
  "finalPrice": "decimal(10,2)",
  "paymentMethod": "string",
  "couponId": "string",
  "status": "enum(pending,paid,failed,refunded)",
  "paymentTime": "timestamp",
  "createTime": "timestamp",
  "updateTime": "timestamp",
  "INDEX(userId, status)",
  "INDEX(createTime)"
}
```

---

## ⚡ 性能与限制

### 频率限制
- **用户发言**：每分钟最多30条消息
- **认同操作**：每个消息只能认同一次，每分钟最多50次认同
- **角色切换**：每小时最多10次
- **技能升级**：每个技能每天最多升级3次（付费无限制）

### 数据限制  
- **消息长度**：最大1000字符
- **房间人数**：最大100人同时在线
- **同时拥有角色**：普通用户64个，VIP用户无限制
- **技能数量**：每个角色最多20个技能

### 性能要求
- **WebSocket消息延迟**：< 100ms
- **HTTP API响应时间**：< 500ms
- **AI首次响应时间**：< 3秒
- **技能经验计算**：< 200ms
- **并发WebSocket连接**：支持10000+连接

---

## 🎯 开发优先级

### P0（核心功能）
1. 基础MBTI角色系统（16个免费角色）
2. 用户认证和WebSocket通信
3. 房间管理和基本消息收发
4. 技能经验基础计算

### P1（重要功能）  
1. 付费角色购买系统
2. 技能升级和解锁机制
3. 话题匹配度算法优化
4. 商业化支付系统

### P2（优化功能）
1. VIP会员系统
2. 角色商店和推荐系统
3. 高级技能组合效果
4. 数据分析和运营后台

---

**备注：此文档为多维度MBTI角色生态系统的完整设计规范，重点体现了角色多样性、技能成长机制和商业化模式的有机结合。建议优先实现P0功能，确保基础体验后再逐步完善付费功能。** 