-- 数据库初始化脚本
-- 创建数据库和基本配置

-- 设置字符编码
SET client_encoding = 'UTF8';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建索引优化查询性能
-- 这些索引将在模型创建表后自动创建，这里仅作为参考

-- 用户相关索引
-- CREATE INDEX IF NOT EXISTS idx_users_openid ON users(openid);
-- CREATE INDEX IF NOT EXISTS idx_users_create_time ON users(create_time);

-- 角色相关索引  
-- CREATE INDEX IF NOT EXISTS idx_character_definitions_dimension ON character_definitions(dimension);
-- CREATE INDEX IF NOT EXISTS idx_user_characters_user_id ON user_characters(user_id);

-- 消息相关索引
-- CREATE INDEX IF NOT EXISTS idx_messages_room_id_create_time ON messages(room_id, create_time);
-- CREATE INDEX IF NOT EXISTS idx_messages_from_user_id ON messages(from_user_id);

-- 技能相关索引
-- CREATE INDEX IF NOT EXISTS idx_skill_progress_user_character ON skill_progress(user_id, character_id);
-- CREATE INDEX IF NOT EXISTS idx_skill_experience_log_create_time ON skill_experience_log(create_time);

-- 订单相关索引
-- CREATE INDEX IF NOT EXISTS idx_orders_user_id_status ON orders(user_id, status);
-- CREATE INDEX IF NOT EXISTS idx_orders_create_time ON orders(create_time);

-- 初始化完成
SELECT 'Database initialization completed' as status; 