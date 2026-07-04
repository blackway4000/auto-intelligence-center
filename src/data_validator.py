"""Data validation for Auto Intelligence Center.

Validates vehicle data before ingestion to prevent incorrect information
from being published. Maintains audience trust.
"""

import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataValidator:
    """Validate vehicle data fields with sensible rules."""
    
    # Price limits (in 万元)
    MIN_PRICE = 1.0
    MAX_PRICE = 200.0
    
    # Date limits
    MIN_DATE = date(2020, 1, 1)
    MAX_DATE = date(2030, 12, 31)
    
    # Dimension limits (mm)
    MIN_LENGTH = 2000
    MAX_LENGTH = 6500
    MIN_WIDTH = 1000
    MAX_WIDTH = 2500
    MIN_HEIGHT = 1000
    MAX_HEIGHT = 2500
    MIN_WHEELBASE = 1500
    MAX_WHEELBASE = 4500
    
    # Range limits (km)
    MIN_RANGE = 50
    MAX_RANGE = 1500
    
    # Battery limits (kWh)
    MIN_BATTERY = 10
    MAX_BATTERY = 200
    
    # Valid vehicle name patterns
    NAME_PATTERN = re.compile(r'^[一-龥a-zA-Z0-9\s\-·]+$', re.UNICODE)
    
    # Known brand names (expand as needed)
    KNOWN_BRANDS = {
        '小鹏', '零跑', '小米', '比亚迪', '问界', '阿维塔', '理想', '蔚来',
        '乐道', '特斯拉', '吉利', '银河', '极氪', '长安', '深蓝', '启源',
        '长城', '哈弗', '坦克', '魏牌', '欧拉', '奇瑞', '星途', '捷途',
        'iCAR', '风云', '大众', '丰田', '本田', '日产', '别克', '福特',
        '宝马', '奔驰', '奥迪', '保时捷', '沃尔沃', '现代', '起亚', '名爵',
        '荣威', '宝骏', '五菱', '哪吒', '岚图', '猛士', '昊铂', '埃安',
        '传祺', '影豹', '极狐', '阿尔法', '智己', '飞凡', '智界', '享界',
        '尊界', '尚界', '一汽', '上汽', '广汽', '东风', '北汽',
    }
    
    @classmethod
    def validate_price(cls, min_price: Optional[float], max_price: Optional[float],
                       price_type: str = '') -> Tuple[bool, List[str]]:
        """Validate price data.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if min_price is None:
            errors.append("价格不能为空")
            return False, errors
        
        if min_price <= 0:
            errors.append(f"价格必须大于0，当前：{min_price}")
        
        if min_price < cls.MIN_PRICE:
            errors.append(f"价格{min_price}万过低，疑似错误（最低允许{cls.MIN_PRICE}万）")
        
        if min_price > cls.MAX_PRICE:
            errors.append(f"价格{min_price}万过高，疑似错误（最高允许{cls.MAX_PRICE}万）")
        
        if max_price is not None:
            if max_price < min_price:
                errors.append(f"最高价{max_price}万低于最低价{min_price}万")
            
            price_range = max_price - min_price
            if price_range > 50:
                errors.append(f"价格跨度{price_range:.1f}万过大，请确认")
        
        # Price type validation
        valid_types = {'预售价', '指导价', '上市价', '官方价', '终端价', '补贴后'}
        if price_type and price_type not in valid_types:
            # Allow but warn
            pass
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_date(cls, date_str: Optional[str], field_name: str = '日期') -> Tuple[bool, List[str]]:
        """Validate date string (YYYY-MM-DD format)."""
        errors = []
        
        if not date_str:
            return True, []  # Optional field
        
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f"{field_name}格式错误：'{date_str}'，应为YYYY-MM-DD")
            return False, errors
        
        if d < cls.MIN_DATE:
            errors.append(f"{field_name}{date_str}过早，疑似错误")
        
        if d > cls.MAX_DATE:
            errors.append(f"{field_name}{date_str}过晚，疑似错误")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_dimensions(cls, length: Optional[int], width: Optional[int],
                           height: Optional[int], wheelbase: Optional[int]) -> Tuple[bool, List[str]]:
        """Validate vehicle dimensions."""
        errors = []
        
        dims = [
            ('长度', length, cls.MIN_LENGTH, cls.MAX_LENGTH),
            ('宽度', width, cls.MIN_WIDTH, cls.MAX_WIDTH),
            ('高度', height, cls.MIN_HEIGHT, cls.MAX_HEIGHT),
            ('轴距', wheelbase, cls.MIN_WHEELBASE, cls.MAX_WHEELBASE),
        ]
        
        for name, value, min_val, max_val in dims:
            if value is None:
                continue
            if value < min_val:
                errors.append(f"车身尺寸{name}{value}mm过小，疑似错误")
            if value > max_val:
                errors.append(f"车身尺寸{name}{value}mm过大，疑似错误")
        
        # Check aspect ratio (length should be > width > height)
        if length and width and height:
            if length < width:
                errors.append(f"长度{length}mm小于宽度{width}mm，请检查")
            if width < height:
                errors.append(f"宽度{width}mm小于高度{height}mm，请检查")
            
            # Typical SUV ratio checks
            ratio = length / width if width > 0 else 0
            if ratio > 3:
                errors.append(f"长宽比{ratio:.1f}异常，请检查尺寸数据")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_range(cls, range_val) -> Tuple[bool, List[str]]:
        """Validate CLTC range (accepts int or string like '510/600')."""
        errors = []
        
        if range_val is None:
            return True, []
        
        # Handle string ranges like "510/600"
        if isinstance(range_val, str):
            parts = range_val.replace(',', '/').split('/')
            nums = []
            for p in parts:
                try:
                    nums.append(int(float(p.strip())))
                except ValueError:
                    continue
            if not nums:
                return True, []  # Skip validation for non-numeric strings
            range_val = max(nums)
        
        if range_val < cls.MIN_RANGE:
            errors.append(f"续航{range_val}km过低，疑似错误")
        
        if range_val > cls.MAX_RANGE:
            errors.append(f"续航{range_val}km过高，疑似错误")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_battery(cls, capacity: Optional[float]) -> Tuple[bool, List[str]]:
        """Validate battery capacity."""
        errors = []
        
        if capacity is None:
            return True, []
        
        if capacity < cls.MIN_BATTERY:
            errors.append(f"电池容量{capacity}kWh过低，疑似错误")
        
        if capacity > cls.MAX_BATTERY:
            errors.append(f"电池容量{capacity}kWh过高，疑似错误")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_vehicle_name(cls, name: str, brand_name: str = '') -> Tuple[bool, List[str]]:
        """Validate vehicle name."""
        errors = []
        
        if not name or not name.strip():
            errors.append("车型名称不能为空")
            return False, errors
        
        if len(name) > 50:
            errors.append(f"车型名称过长：{name}")
        
        if not cls.NAME_PATTERN.match(name):
            errors.append(f"车型名称包含非法字符：{name}")
        
        # Check if brand is in name (common pattern, allow partial match)
        if brand_name:
            # Extract brand keyword (e.g., "小鹏汽车" -> "小鹏")
            brand_keyword = brand_name.replace('汽车', '').replace('新能源', '').replace('有限公司', '')
            if brand_keyword not in name:
                errors.append(f"车型名'{name}'未包含品牌关键词'{brand_keyword}'，请确认")
        
        # Check if brand is known
        if brand_name:
            brand_found = False
            for known in cls.KNOWN_BRANDS:
                if known in brand_name:
                    brand_found = True
                    break
            if not brand_found:
                errors.append(f"品牌'{brand_name}'不在已知品牌列表中，请确认")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_source_url(cls, url: Optional[str]) -> Tuple[bool, List[str]]:
        """Validate source URL."""
        errors = []
        
        if not url:
            errors.append("数据来源URL不能为空（必须标注数据来源）")
            return False, errors
        
        if not url.startswith(('http://', 'https://')):
            errors.append(f"数据来源URL格式错误：{url}")
        
        # Check for known reliable sources
        reliable_domains = [
            'xiaopeng.com', 'leapmotor.com', 'miit.gov.cn',
            'autohome.com.cn', 'dongchedi.com', 'yiche.com',
            'weibo.com', 'toutiao.com', '163.com', 'sina.com',
            'byd.com', 'lixiang.com', 'nio.com', 'xpeng.com',
        ]
        
        is_reliable = any(domain in url for domain in reliable_domains)
        if not is_reliable:
            # Warning only, not error
            pass
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_full_vehicle(cls, data: Dict) -> Tuple[bool, List[str]]:
        """Validate all vehicle data fields.
        
        Supports both data_collector field names (vehicle_name, price_min)
        and database field names (name, min_price).
        
        Args:
            data: Dict with vehicle data
        
        Returns:
            (is_valid, error_messages)
        """
        all_errors = []
        
        # Name validation (support both vehicle_name and name)
        name = data.get('vehicle_name') or data.get('name', '')
        brand_name = data.get('brand_name', '')
        valid, errors = cls.validate_vehicle_name(name, brand_name)
        all_errors.extend(errors)
        
        # Price validation (support both price_min and min_price)
        min_price = data.get('price_min') if data.get('price_min') is not None else data.get('min_price')
        max_price = data.get('price_max') if data.get('price_max') is not None else data.get('max_price')
        valid, errors = cls.validate_price(
            min_price,
            max_price,
            data.get('price_type', '')
        )
        all_errors.extend(errors)
        
        # Date validations
        for field in ['launch_date', 'presale_date', 'announce_date']:
            valid, errors = cls.validate_date(data.get(field), field)
            all_errors.extend(errors)
        
        # Dimension validation
        valid, errors = cls.validate_dimensions(
            data.get('length'),
            data.get('width'),
            data.get('height'),
            data.get('wheelbase')
        )
        all_errors.extend(errors)
        
        # Range validation (support both range_cltc and string range values)
        range_val = data.get('range_cltc')
        if range_val is None and 'specs' in data:
            range_val = data['specs'].get('range_cltc')
        valid, errors = cls.validate_range(range_val)
        all_errors.extend(errors)
        
        # Battery validation
        battery = data.get('battery_capacity')
        if battery is None and 'specs' in data:
            battery = data['specs'].get('battery_capacity')
        valid, errors = cls.validate_battery(battery)
        all_errors.extend(errors)
        
        # Source URL validation
        valid, errors = cls.validate_source_url(data.get('source_url'))
        all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors


def validate_before_insert(data: Dict, raise_on_error: bool = True):
    """Validate data before inserting to database.
    
    Args:
        data: Vehicle data dict
        raise_on_error: If True, raises ValidationError on failure
    
    Returns:
        is_valid boolean
    
    Raises:
        ValidationError: If data is invalid and raise_on_error is True
    """
    is_valid, errors = DataValidator.validate_full_vehicle(data)
    
    if not is_valid:
        error_msg = "数据校验失败：\n" + "\n".join(f"  - {e}" for e in errors)
        print(error_msg)
        if raise_on_error:
            raise ValidationError(error_msg)
    
    return is_valid


if __name__ == '__main__':
    # Test validation
    test_cases = [
        {
            'name': '小鹏MONA L03',
            'brand_name': '小鹏汽车',
            'min_price': 14.38,
            'max_price': 16.18,
            'price_type': '预售价',
            'launch_date': '2026-07-15',
            'length': 4650,
            'width': 1920,
            'height': 1600,
            'wheelbase': 2850,
            'range_cltc': 600,
            'battery_capacity': 67.1,
            'source_url': 'https://www.xiaopeng.com',
        },
        {
            'name': '测试错误车',
            'brand_name': '未知品牌',
            'min_price': -5,
            'max_price': 3,
            'launch_date': '2015-01-01',
            'length': 1000,
            'width': 5000,
            'height': 300,
            'range_cltc': 2000,
            'source_url': '',
        },
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test.get('name', '未知')}")
        print("=" * 50)
        try:
            validate_before_insert(test, raise_on_error=True)
            print("✅ 校验通过")
        except ValidationError as e:
            print(e)
