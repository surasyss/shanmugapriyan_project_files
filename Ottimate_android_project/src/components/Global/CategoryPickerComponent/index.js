import React, { Component } from 'react';
import {
  FlatList, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';
import SearchBar from '../../qubiqle/SearchBar';
import Loader from '../../qubiqle/Loader';

export default class CategoryPickerComponent extends Component {
  renderSearch() {
    const {
      loadNextPage, searchText, changeSearchQuery
    } = this.props;

    return (
      <SearchBar
        onSearchCancel={async () => {
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
        placeholder="Search Category"
      />
    );
  }

  render() {
    const {
      categories, loading, loadNextPage, firstLoad, onSelect
    } = this.props;

    let refreshing = categories.length !== 0 && firstLoad;
    if (!refreshing) refreshing = false;
    return (
      <View>
        {this.renderSearch()}

        <FlatList
          data={categories}
          renderItem={({ item, index }) => (
            <TouchableOpacity
              key={index}
              style={styles.categoryContainer}
              onPress={() => {
                if (onSelect) {
                  onSelect(item);
                }
              }}
            >
              <Text style={styles.title}>{item.name}</Text>
            </TouchableOpacity>
          )}
          onEndReached={() => {
            loadNextPage();
          }}
          ListFooterComponent={
            categories.length
              ? (
                <Loader
                  loading={loading}
                />
              ) : null
          }
          refreshing={refreshing}
          onRefresh={() => loadNextPage(1)}
          keyExtractor={(item) => item.id.toString()}
          ItemSeparatorComponent={() => (
            <View
              style={styles.divider}
            />
          )}
        />
      </View>
    );
  }
}
