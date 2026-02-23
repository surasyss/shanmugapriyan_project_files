import AsyncStorage from '@react-native-community/async-storage';

class Async {
  static async get(key) {
    try {
      const retrievedItem = await AsyncStorage.getItem(key);
      return JSON.parse(retrievedItem);
    } catch (error) {
      return null;
    }
  }

  static async set(key, value) {
    await AsyncStorage.setItem(key, JSON.stringify(value));
  }

  static async remove(key) {
    return AsyncStorage.removeItem(key);
  }
}

export default Async;
