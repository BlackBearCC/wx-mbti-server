"""
订单和支付相关数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, DECIMAL, Enum
from sqlalchemy.sql import func
from app.config.database import Base
import uuid
import enum


class ProductType(str, enum.Enum):
    """产品类型"""
    CHARACTER = "character"
    SKILL = "skill"
    VIP = "vip"
    BUNDLE = "bundle"


class OrderStatus(str, enum.Enum):
    """订单状态"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    """支付方式"""
    WECHAT_PAY = "wechat_pay"
    ALIPAY = "alipay"
    BALANCE = "balance"  # 账户余额


class Order(Base):
    """订单表"""
    __tablename__ = "orders"
    
    order_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # 产品信息
    product_type = Column(Enum(ProductType), nullable=False)
    product_id = Column(String, nullable=False)
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    
    # 价格信息
    original_price = Column(DECIMAL(10, 2), nullable=False)
    discount_price = Column(DECIMAL(10, 2), nullable=True)
    final_price = Column(DECIMAL(10, 2), nullable=False)
    
    # 优惠信息
    coupon_id = Column(String, nullable=True)
    coupon_discount = Column(DECIMAL(10, 2), default=0, nullable=False)
    
    # 支付信息
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_id = Column(String, nullable=True)  # 第三方支付ID
    
    # 订单状态
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    # 来源信息
    source = Column(String(50), nullable=True)  # 购买来源
    platform = Column(String(50), nullable=True)  # 平台信息
    
    # 时间戳
    payment_time = Column(DateTime(timezone=True), nullable=True)
    expire_time = Column(DateTime(timezone=True), nullable=True)  # 订单过期时间
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 额外信息
    metadata = Column(JSON, nullable=True)  # 额外元数据
    notes = Column(Text, nullable=True)  # 备注
    
    def __repr__(self):
        return f"<Order(order_id='{self.order_id}', user_id='{self.user_id}', status='{self.status}')>"


class PaymentTransaction(Base):
    """支付交易表"""
    __tablename__ = "payment_transactions"
    
    transaction_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # 支付信息
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="CNY", nullable=False)
    
    # 第三方支付信息
    third_party_id = Column(String, nullable=True)  # 微信/支付宝交易号
    prepay_id = Column(String, nullable=True)  # 预支付ID
    
    # 交易状态
    status = Column(String(20), default="pending", nullable=False)
    # pending, success, failed, cancelled, refunding, refunded
    
    # 支付参数 (JSON格式)
    payment_params = Column(JSON, nullable=True)
    # 示例: {"timeStamp": "...", "nonceStr": "...", "package": "...", "signType": "...", "paySign": "..."}
    
    # 回调信息
    callback_data = Column(JSON, nullable=True)  # 支付回调数据
    callback_time = Column(DateTime(timezone=True), nullable=True)
    
    # 时间戳
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<PaymentTransaction(transaction_id='{self.transaction_id}', order_id='{self.order_id}')>"


class Coupon(Base):
    """优惠券表"""
    __tablename__ = "coupons"
    
    coupon_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False, index=True)
    
    # 优惠券信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 优惠类型和金额
    discount_type = Column(String(20), nullable=False)  # fixed, percentage
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    min_amount = Column(DECIMAL(10, 2), default=0, nullable=False)  # 最低消费金额
    max_discount = Column(DECIMAL(10, 2), nullable=True)  # 最大优惠金额
    
    # 适用范围
    applicable_products = Column(JSON, nullable=True)  # 适用产品列表
    applicable_types = Column(JSON, nullable=True)  # 适用产品类型
    
    # 使用限制
    total_limit = Column(Integer, nullable=True)  # 总使用次数限制
    user_limit = Column(Integer, default=1, nullable=False)  # 每用户使用次数限制
    used_count = Column(Integer, default=0, nullable=False)  # 已使用次数
    
    # 有效期
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Coupon(coupon_id='{self.coupon_id}', code='{self.code}')>"


class UserCoupon(Base):
    """用户优惠券使用记录表"""
    __tablename__ = "user_coupons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    coupon_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=True, index=True)  # 使用的订单ID
    
    # 使用信息
    discount_amount = Column(DECIMAL(10, 2), nullable=False)  # 实际优惠金额
    use_time = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<UserCoupon(user_id='{self.user_id}', coupon_id='{self.coupon_id}')>"


class UserBalance(Base):
    """用户余额表"""
    __tablename__ = "user_balances"
    
    user_id = Column(String, primary_key=True)
    balance = Column(DECIMAL(10, 2), default=0, nullable=False)
    frozen_balance = Column(DECIMAL(10, 2), default=0, nullable=False)  # 冻结余额
    
    # 时间戳
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserBalance(user_id='{self.user_id}', balance='{self.balance}')>"


class BalanceTransaction(Base):
    """余额交易记录表"""
    __tablename__ = "balance_transactions"
    
    transaction_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=True, index=True)
    
    # 交易信息
    type = Column(String(20), nullable=False)  # recharge, consume, refund, reward
    amount = Column(DECIMAL(10, 2), nullable=False)
    balance_before = Column(DECIMAL(10, 2), nullable=False)
    balance_after = Column(DECIMAL(10, 2), nullable=False)
    
    # 描述信息
    description = Column(String(255), nullable=True)
    reference_id = Column(String, nullable=True)  # 关联ID
    
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<BalanceTransaction(user_id='{self.user_id}', type='{self.type}', amount='{self.amount}')>" 