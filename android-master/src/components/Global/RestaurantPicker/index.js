import React, { Component } from 'react';
import {
  View, FlatList, Text, TouchableOpacity
} from 'react-native';
import styles from './styles';
import SearchBar from '../../qubiqle/SearchBar';
import Adapter from '../../../utils/Adapter';

export default class RestaurantPicker extends Component {
  // eslint-disable-next-line no-unused-vars,no-empty-pattern
  static navigationOptions = ({ navigation }) => ({
    title: 'Select Location'
  });

  constructor(props) {
    super(props);
    this.state = {
      restaurants: [],
      filteredRestaurants: []
    };
  }

  async componentDidMount() {
    const restaurants = await Adapter.getRestaurants();
    this.setState({ restaurants, filteredRestaurants: restaurants });
  }

  renderSearch() {
    const {
      loadNextPage, searchText, isSearchVisible, openSearch, changeSearchQuery
    } = this.props;

    if (isSearchVisible) {
      return (
        <SearchBar
          onSearchCancel={async () => {
            await openSearch(false);
            await changeSearchQuery('');
            loadNextPage(1);
          }}
          onTextChange={(text) => {
            changeSearchQuery(text);
          }}
          searchText={searchText}
          onSubmit={() => {
            loadNextPage(1);
          }}
          placeholder="Search Invoices"
        />
      );
    }

    return (
      <View />
    );
  }

  render() {
    const {
      filteredRestaurants
    } = this.state;

    const { onSelect } = this.props.navigation.state.params;

    return (
      <FlatList
        data={filteredRestaurants}
        renderItem={({ item, index }) => (
          <TouchableOpacity
            key={index}
            style={styles.restaurantContainer}
            onPress={() => {
              if (onSelect) {
                onSelect(item);
              }
              this.props.navigation.goBack();
            }}
          >
            <Text style={styles.title}>{item.name}</Text>
          </TouchableOpacity>
        )}
        keyExtractor={(item) => item.id.toString()}
        ItemSeparatorComponent={() => (
          <View
            style={styles.divider}
          />
        )}
      />
    );
  }
}
