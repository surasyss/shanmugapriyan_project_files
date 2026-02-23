import Async from './storage/Async';
/* eslint-disable no-console */

class Adapter {
  static async get(key) {
    return Async.get(key);
  }

  static async set(key, value) {
    await Async.set(key, value);
  }

  static remove(key) {
    return Async.remove(key).then(() => {
    }).catch(() => {
    });
  }

  static async setUser(user) {
    try {
      await Adapter.set('user', user);
    } catch (error) {
    }
  }

  static async getUser() {
    try {
      const data = await Adapter.get('user');
      return data;
    } catch (e) {
      return null;
    }
  }

  static async logout() {
    await this.remove('user');
    await this.remove('token');
    await this.remove('pending_uploads');
    await this.remove('restaurants');
    await this.remove('token_type');
    await this.remove('pending_transaction_uploads');
  }

  static async setAuthToken(token: any): void {
    if (token) {
      if (token.token_type === 'Bearer') {
        await Adapter.setTokenType('Bearer');
        await Adapter.setToken(token.access_token);
      } else {
        await Adapter.setTokenType('Token');
        await Adapter.setToken(token);
      }
    } else {
      await Adapter.setTokenType(null);
      await Adapter.setToken(null);
    }
  }

  static async setToken(token) {
    try {
      await Adapter.set('token', token);
    } catch (error) {
    }
  }

  static async getToken() {
    try {
      let token_type = await Adapter.get('token_type');
      if (!token_type) token_type = 'Token';
      const token = await Adapter.get('token');
      if (token && token_type) {
        return `${token_type} ${token}`;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  static async setTokenType(token_type) {
    try {
      await Adapter.set('token_type', token_type);
    } catch (error) {
    }
  }

  static async getAuthHeader() {
    try {
      const token = await this.getToken();
      if (token) {
        return {
          Authorization: token,
          'IF-MODIFIED-SINCE': '1900-01-01'
        };
      }
    } catch (e) {
      return null;
    }
    return null;
  }

  static async setRestaurants(restaurants) {
    try {
      await Adapter.set('restaurants', restaurants);
    } catch (error) {
    }
  }

  static async getRestaurants() {
    try {
      const data = await Adapter.get('restaurants');
      return data;
    } catch (e) {
      return null;
    }
  }

  static async setCompanies(companies) {
    try {
      await Adapter.set('companies', companies);
    } catch (error) {
    }
  }

  static async getCompanies() {
    try {
      const data = await Adapter.get('companies');
      return data;
    } catch (e) {
      return null;
    }
  }

  static async setCurrentCompany(company) {
    if (company) {
      try {
        await Adapter.set('currentCompany', company);
      } catch (error) {
      }
    }
  }

  static async getCurrentCompany() {
    try {
      return await Adapter.get('currentCompany');
    } catch (e) {
      return null;
    }
  }

  static async showChequeruns() {
    const user = await this.getUser();
    const { preferences } = user;
    if (preferences) {
      const { billpayShowChequeRuns } = preferences;
      if (billpayShowChequeRuns) {
        return billpayShowChequeRuns.enabled;
      }
    }
    return false;
  }

  static async hasBillpayPermission() {
    const user = await this.getUser();
    const { permissions } = user;
    let containsBillpay = false;
    // eslint-disable-next-line no-restricted-syntax
    for (const permission of permissions) {
      if (permission.indexOf('billpay.') !== -1) {
        containsBillpay = true;
        break;
      }
    }
    return containsBillpay;
  }
}

export default Adapter;
